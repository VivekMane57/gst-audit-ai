"""
services/audit_service.py  (Fixed + Enhanced)
-----------------------------------------------
Fixes from previous version:
  1. CONSISTENCY BUG: issues passed to PDF/email now from same source as DB save
  2. issues_json now uses to_structured_dict() — consistent structured output
  3. Notice sim uses to_notice_sim_dict() — no more scattered dict building
  4. AuditResponse populated with NoticeOutput + IssueSummary
  5. _generate_pdf now passes actual issues (not empty list!)
  6. Email now includes top_risk_reasons + estimated_penalty_exposure

Architecture: service stays thin — delegates to repositories.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.dependencies import AuditDeps
from app.services.file_router import parse_any_file
from app.services.audit_engine import run_all_checks
from app.services.sector_checks import run_sector_checks
from app.services.score_calculator import calculate_score, ScoreResult
from app.services.notice_simulator import run_notice_simulation
from app.services.email_service import send_audit_complete_to_ca, send_high_risk_alert
from app.services.report_generator import generate_pdf
from app.models.audit import AuditResponse, ITCSummary, IssueSummary, NoticeOutput, WhatIfResult
from app.models.issue import Issue

logger = logging.getLogger(__name__)

VALID_SECTORS = {
    "healthcare", "retail", "manufacturing",
    "it_services", "real_estate", "restaurant", "export_import"
}


class AuditService:
    def __init__(self, deps: AuditDeps):
        self.deps = deps

    def run(
        self,
        sales_bytes:       Optional[bytes],
        sales_filename:    Optional[str],
        purchase_bytes:    Optional[bytes],
        purchase_filename: Optional[str],
        extra_files:       list[tuple[bytes, str]],
        our_gstin:         str,
        period:            str,
        language:          str           = "en",
        sector:            Optional[str] = None,
        client_id:         Optional[str] = None,
        filing_delays:     int           = 0,
        turnover_cr:       float         = 1.0,
        previous_notices:  int           = 0,
    ) -> dict:

        # Step 1 — Parse files
        all_invoices, files_parsed, parse_errors = self._parse_files(
            sales_bytes, sales_filename,
            purchase_bytes, purchase_filename,
            extra_files, our_gstin, period,
        )
        if not all_invoices:
            detail = "No invoices could be extracted from uploaded files."
            if parse_errors:
                detail += f" Errors: {'; '.join(parse_errors[:3])}"
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail=detail)

        # Step 2 — Audit engine
        issues: list[Issue] = run_all_checks(all_invoices, our_gstin=our_gstin, period=period)
        if sector and sector in VALID_SECTORS:
            issues.extend(run_sector_checks(all_invoices, sector=sector, our_gstin=our_gstin))

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        issues.sort(key=lambda x: severity_order.get(x.severity.value, 99))

        # Step 3 — Score
        score_result: ScoreResult = calculate_score(issues)

        # ── SINGLE SOURCE OF TRUTH for issue data ─────────────
        # Use to_structured_dict() for all downstream consumers
        # This prevents the "No issues found" contradiction bug
        issues_json = [issue.to_structured_dict(lang=language) for issue in issues]

        # Counts — derived from actual issues list
        issue_summary = IssueSummary.from_issues(issues)
        itc_at_risk   = sum(i.itc_at_risk for i in issues)
        itc_blocked   = sum(i.itc_at_risk for i in issues if i.issue_type.value == "gstr2b_missing")

        # Step 4 — Notice simulation
        # Use centralized to_notice_sim_dict() — no more scattered conversions
        notice_sim = run_notice_simulation(
            issues           = [i.to_notice_sim_dict() for i in issues],
            compliance_score = score_result.score,
            client_name      = "",
            client_gstin     = our_gstin,
            lang             = language,
            filing_delays    = filing_delays,
            turnover_cr      = turnover_cr,
            previous_notices = previous_notices,
        )

        # Step 5 — Client name
        client_name = None
        if client_id:
            client_name = self.deps.client_repo.get_name(client_id, self.deps.ca_id)

        # Step 6 — DB save
        audit_id     = str(uuid.uuid4())
        gstin_masked = (
            f"{our_gstin[:2]}{'*' * 10}{our_gstin[-3:]}"
            if len(our_gstin) == 15 else our_gstin
        )
        audit_record = self._build_record(
            audit_id, gstin_masked, period, language, sector,
            client_id, client_name, all_invoices, score_result,
            issues_json, issue_summary, itc_at_risk, itc_blocked,
            notice_sim,
        )
        self.deps.audit_repo.insert(audit_record)

        if client_id:
            self.deps.client_repo.update_last_score(client_id, self.deps.ca_id, score_result.score)

        # Step 7 — Build AuditResponse (source of truth for PDF + email)
        audit_obj = self._build_audit_response(
            audit_id, gstin_masked, period, language,
            score_result, all_invoices, issues, issue_summary,
            itc_at_risk, itc_blocked, notice_sim, client_name,
        )

        # Step 8 — PDF (uses audit_obj — same data as DB)
        pdf_bytes = self._generate_pdf(audit_obj, client_name or "Client")

        # Step 9 — Emails (uses audit_obj + notice_sim enriched data)
        self._send_emails(
            audit_obj   = audit_obj,
            notice_sim  = notice_sim,
            issues      = issues,
            client_id   = client_id,
            client_name = client_name,
            our_gstin   = our_gstin,
            period      = period,
            audit_id    = audit_id,
            pdf_bytes   = pdf_bytes,
        )

        return {
            "audit_id":                   audit_id,
            "compliance_score":           score_result.score,
            "risk_level":                 score_result.risk_level,
            "total_invoices":             len(all_invoices),
            "files_parsed":               files_parsed,
            "parse_errors":               parse_errors[:5] if parse_errors else [],
            "issues":                     issues_json,
            "issue_summary":              issue_summary.dict(),
            "itc_at_risk":                itc_at_risk,
            # Legacy severity counts — kept for backward compat
            "critical_count":             issue_summary.critical,
            "high_count":                 issue_summary.high,
            "medium_count":               issue_summary.medium,
            "low_count":                  issue_summary.low,
            "notice_simulation":          notice_sim,
            "top_risk_reasons":           notice_sim.get("top_risk_reasons", []),
            "estimated_penalty_exposure": notice_sim.get("estimated_penalty_exposure", 0),
            "pdf_generated":              pdf_bytes is not None,
            "message":                    "Audit complete",
        }

    # ── Build AuditResponse ───────────────────────────────────
    def _build_audit_response(
        self,
        audit_id, gstin_masked, period, language,
        score_result, all_invoices, issues, issue_summary,
        itc_at_risk, itc_blocked, notice_sim, client_name,
    ) -> AuditResponse:
        """
        Build AuditResponse — single source of truth for PDF and email.
        Both use this object — no data divergence possible.
        """
        from app.services.score_calculator import get_risk_level_translated

        # Build NoticeOutput from notice_sim
        what_if_raw = notice_sim.get("what_if_fix_all", {})
        notice_output = NoticeOutput(
            probability               = notice_sim["probability"],
            risk_level                = notice_sim["risk_level"],
            risk_message              = notice_sim["risk_message"],
            top_risk_reasons          = notice_sim.get("top_risk_reasons", []),
            estimated_penalty_exposure = notice_sim.get("estimated_penalty_exposure", 0.0),
            if_fixed_risk_drop        = WhatIfResult(**what_if_raw) if what_if_raw else None,
            possible_notices          = notice_sim.get("possible_notices", []),
            recommendations           = notice_sim.get("recommendations", []),
            risk_areas                = notice_sim.get("risk_areas", []),
        )

        return AuditResponse(
            audit_id              = audit_id,
            client_gstin_masked   = gstin_masked,
            period                = period,
            language              = language,
            compliance_score      = score_result.score,
            risk_level            = score_result.risk_level,
            risk_level_translated = get_risk_level_translated(score_result.score, language),
            total_invoices        = len(all_invoices),
            issues                = issues,
            issue_summary         = issue_summary,
            critical_count        = issue_summary.critical,
            high_count            = issue_summary.high,
            medium_count          = issue_summary.medium,
            low_count             = issue_summary.low,
            itc_summary           = ITCSummary(
                at_risk  = itc_at_risk,
                blocked  = itc_blocked,
                total    = itc_at_risk + itc_blocked,
                eligible = 0.0,
            ),
            notice_output = notice_output,
            created_at    = datetime.now(timezone.utc).isoformat(),
        )

    # ── Build DB record ───────────────────────────────────────
    def _build_record(
        self, audit_id, gstin_masked, period, language, sector,
        client_id, client_name, all_invoices, score_result,
        issues_json, issue_summary: IssueSummary,
        itc_at_risk, itc_blocked, notice_sim,
    ) -> dict:
        return {
            "id":                     audit_id,
            "user_id":                self.deps.user_uuid,
            "ca_id":                  self.deps.ca_id,
            "client_id":              client_id,
            "client_name":            client_name,
            "client_gstin_masked":    gstin_masked,
            "period":                 period,
            "language":               language,
            "sector":                 sector,
            "total_invoices_scanned": len(all_invoices),
            "compliance_score":       score_result.score,
            "risk_level":             score_result.risk_level,
            "issues_json":            issues_json,      # structured dicts
            "itc_at_risk":            round(itc_at_risk, 2),
            "itc_blocked":            round(itc_blocked, 2),
            "itc_eligible":           0.0,
            "itc_summary": {
                "at_risk":      round(itc_at_risk, 2),
                "blocked":      round(itc_blocked, 2),
                "total_impact": round(itc_at_risk + itc_blocked, 2),
            },
            # Structured issue counts
            "critical_count":         issue_summary.critical,
            "high_count":             issue_summary.high,
            "medium_count":           issue_summary.medium,
            "low_count":              issue_summary.low,
            "total_issues":           issue_summary.total,
            # Notice predictor data
            "notice_probability":     notice_sim["probability"],
            "notice_risk_level":      notice_sim["risk_level"],
            "estimated_penalty_exposure": notice_sim.get("estimated_penalty_exposure", 0),
            "top_risk_reasons":       notice_sim.get("top_risk_reasons", []),
            "notice_simulation": {
                "probability":            notice_sim["probability"],
                "risk_level":             notice_sim["risk_level"],
                "risk_message":           notice_sim["risk_message"],
                "risk_areas":             notice_sim["risk_areas"],
                "possible_notices":       notice_sim["possible_notices"],
                "what_if_fix_all":        notice_sim["what_if_fix_all"],
                "recommendations":        notice_sim["recommendations"][:5],
                "top_risk_reasons":       notice_sim.get("top_risk_reasons", []),
                "estimated_penalty_exposure": notice_sim.get("estimated_penalty_exposure", 0),
                "issue_summary":          notice_sim.get("issue_summary", {}),
            },
        }

    # ── PDF — uses AuditResponse (consistent with DB) ─────────
    def _generate_pdf(
        self,
        audit_obj: AuditResponse,
        client_name: str,
    ) -> Optional[bytes]:
        try:
            pdf_bytes = generate_pdf(
                audit_obj,
                ca_name     = self.deps.ca_name,
                client_name = client_name,
                lang        = audit_obj.language,
            )
            logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.error(f"PDF generation failed (non-fatal): {e}", exc_info=True)
            return None

    # ── Email — uses audit_obj for consistency ────────────────
    def _send_emails(
        self,
        audit_obj:  AuditResponse,
        notice_sim: dict,
        issues:     list[Issue],
        client_id:  Optional[str],
        client_name: Optional[str],
        our_gstin:  str,
        period:     str,
        audit_id:   str,
        pdf_bytes:  Optional[bytes],
    ) -> None:
        try:
            ca_email = self.deps.ca_email
            ca_name  = self.deps.ca_name

            # Use audit_obj.get_issue_summary() — consistent with actual issues
            issue_summary = audit_obj.get_issue_summary()

            email_params = dict(
                ca_name        = ca_name,
                client_name    = client_name or "Client",
                client_gstin   = our_gstin,
                period         = period,
                score          = audit_obj.compliance_score,
                risk_level     = audit_obj.risk_level,
                issues_count   = issue_summary.total,
                critical_count = issue_summary.critical,
                itc_at_risk    = float(audit_obj.itc_summary.at_risk),
                notice_prob    = notice_sim["probability"],
                audit_id       = audit_id,
                pdf_content    = pdf_bytes,
                # NEW fields
                top_risk_reasons           = notice_sim.get("top_risk_reasons", []),
                estimated_penalty_exposure = notice_sim.get("estimated_penalty_exposure", 0),
            )

            if ca_email:
                sent = send_audit_complete_to_ca(ca_email=ca_email, is_client=False, **email_params)
                logger.info(f"CA email {'sent' if sent else 'failed'} → {ca_email}")

            if ca_email and notice_sim.get("probability", 0) >= 50:
                send_high_risk_alert(
                    ca_email    = ca_email,
                    ca_name     = ca_name,
                    client_name = client_name or "Client",
                    score       = audit_obj.compliance_score,
                    notice_prob = notice_sim["probability"],
                    issues      = [i.dict() for i in issues if i.severity.value == "CRITICAL"],
                    top_risk_reasons           = notice_sim.get("top_risk_reasons", []),
                    estimated_penalty_exposure = notice_sim.get("estimated_penalty_exposure", 0),
                )

            if client_id:
                contact = self.deps.client_repo.get_contact(client_id, self.deps.ca_id)
                if contact:
                    client_email = self._clean_email(contact.get("email"))
                    if client_email and client_email != ca_email:
                        send_audit_complete_to_ca(
                            ca_email  = client_email,
                            is_client = True,
                            **email_params,
                        )

        except Exception as e:
            logger.warning(f"Email sending failed (non-fatal): {e}", exc_info=True)

    # ── Helpers ───────────────────────────────────────────────
    def _parse_files(self, sales_bytes, sales_filename, purchase_bytes, purchase_filename, extra_files, our_gstin, period):
        all_invoices = []
        files_parsed = 0
        parse_errors = []

        if sales_bytes and sales_filename:
            try:
                inv = parse_any_file(sales_bytes, filename=sales_filename, invoice_type="sale", our_gstin=our_gstin, period=period)
                all_invoices.extend(inv); files_parsed += 1
            except Exception as e:
                parse_errors.append(f"Sales ({sales_filename}): {e}")

        if purchase_bytes and purchase_filename:
            try:
                inv = parse_any_file(purchase_bytes, filename=purchase_filename, invoice_type="purchase", our_gstin=our_gstin, period=period)
                all_invoices.extend(inv); files_parsed += 1
            except Exception as e:
                parse_errors.append(f"Purchase ({purchase_filename}): {e}")

        for f_bytes, f_name in extra_files:
            try:
                fname_lower = f_name.lower()
                inv_type = "sale" if any(k in fname_lower for k in ["sale", "gstr1", "gstr-1", "outward"]) else "purchase"
                inv = parse_any_file(f_bytes, filename=f_name, invoice_type=inv_type, our_gstin=our_gstin, period=period)
                all_invoices.extend(inv); files_parsed += 1
            except Exception as e:
                parse_errors.append(f"{f_name}: {e}")

        return all_invoices, files_parsed, parse_errors

    @staticmethod
    def _clean_email(email: Optional[str]) -> Optional[str]:
        if not email: return None
        email = email.strip()
        if "@placeholder" in email or "auditai.app" in email or "@" not in email: return None
        return email