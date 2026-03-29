"""
services/audit_service.py
--------------------------
All audit business logic — extracted from router.

Router sirf HTTP handle karta hai.
Ye file pure Python — koi FastAPI, koi HTTP, koi async.
Isliye easily testable hai.

Flow:
  1. Parse files
  2. Run audit engine
  3. Score calculation
  4. Notice simulation
  5. DB save (via repository)
  6. PDF generation
  7. Email sending
  8. Return result dict
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
from app.models.audit import AuditResponse, ITCSummary

logger = logging.getLogger(__name__)

VALID_SECTORS = {
    "healthcare", "retail", "manufacturing",
    "it_services", "real_estate", "restaurant", "export_import"
}


class AuditService:
    """
    Audit business logic service.
    Ek AuditDeps inject karo — baaki sab internal.
    """

    def __init__(self, deps: AuditDeps):
        self.deps = deps

    # ── Main entry point ──────────────────────────────────────
    def run(
        self,
        sales_bytes:       Optional[bytes],
        sales_filename:    Optional[str],
        purchase_bytes:    Optional[bytes],
        purchase_filename: Optional[str],
        extra_files:       list[tuple[bytes, str]],   # [(bytes, filename), ...]
        our_gstin:         str,
        period:            str,
        language:          str         = "en",
        sector:            Optional[str] = None,
        client_id:         Optional[str] = None,
        filing_delays:     int         = 0,
        turnover_cr:       float       = 1.0,
        previous_notices:  int         = 0,
    ) -> dict:

        # Step 1 — Parse files
        all_invoices, files_parsed, parse_errors = self._parse_files(
            sales_bytes, sales_filename,
            purchase_bytes, purchase_filename,
            extra_files, our_gstin, period,
        )

        if not all_invoices:
            error_detail = "No invoices could be extracted from uploaded files."
            if parse_errors:
                error_detail += f" Errors: {'; '.join(parse_errors[:3])}"
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail=error_detail)

        # Step 2 — Audit engine
        issues = run_all_checks(all_invoices, our_gstin=our_gstin, period=period)
        if sector and sector in VALID_SECTORS:
            issues.extend(run_sector_checks(all_invoices, sector=sector, our_gstin=our_gstin))

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        issues.sort(key=lambda x: severity_order.get(x.severity.value, 99))

        # Step 3 — Score
        score_result: ScoreResult = calculate_score(issues)

        issues_json    = [issue.dict() for issue in issues]
        itc_at_risk    = sum(i.itc_at_risk for i in issues)
        itc_blocked    = sum(i.itc_at_risk for i in issues if i.issue_type.value == "gstr2b_missing")
        critical_count = sum(1 for i in issues if i.severity.value == "CRITICAL")
        high_count     = sum(1 for i in issues if i.severity.value == "HIGH")
        medium_count   = sum(1 for i in issues if i.severity.value == "MEDIUM")
        low_count      = sum(1 for i in issues if i.severity.value == "LOW")

        # Step 4 — Notice simulation
        notice_sim = run_notice_simulation(
            issues=[
                {
                    "type":       i.issue_type.value,
                    "severity":   i.severity.value.lower(),
                    "invoice":    i.invoice_number,
                    "party":      i.party_name or "N/A",
                    "amount":     self._safe_amount(i),
                    "tax_impact": i.itc_at_risk or 0,
                }
                for i in issues
            ],
            compliance_score = score_result.score,
            client_name      = "",
            client_gstin     = our_gstin,
            lang             = language,
            filing_delays    = filing_delays,
            turnover_cr      = turnover_cr,
            previous_notices = previous_notices,
        )

        # Step 5 — Client name lookup
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
            issues_json, itc_at_risk, itc_blocked,
            critical_count, high_count, medium_count, low_count,
            notice_sim,
        )
        self.deps.audit_repo.insert(audit_record)

        if client_id:
            self.deps.client_repo.update_last_score(client_id, self.deps.ca_id, score_result.score)

        # Step 7 — PDF generation
        pdf_bytes = self._generate_pdf(
            audit_id, gstin_masked, period, language,
            score_result, all_invoices, issues,
            itc_at_risk, itc_blocked,
            critical_count, high_count, medium_count, low_count,
            client_name,
        )

        # Step 8 — Emails
        self._send_emails(
            score_result, notice_sim, issues, client_id,
            client_name, our_gstin, period, audit_id,
            itc_at_risk, critical_count, pdf_bytes,
        )

        return {
            "audit_id":          audit_id,
            "compliance_score":  score_result.score,
            "risk_level":        score_result.risk_level,
            "total_invoices":    len(all_invoices),
            "files_parsed":      files_parsed,
            "parse_errors":      parse_errors[:5] if parse_errors else [],
            "issues":            issues_json,
            "itc_at_risk":       itc_at_risk,
            "critical_count":    critical_count,
            "high_count":        high_count,
            "medium_count":      medium_count,
            "low_count":         low_count,
            "notice_simulation": notice_sim,
            "pdf_generated":     pdf_bytes is not None,
            "message":           "Audit complete",
        }

    # ── Private helpers ───────────────────────────────────────

    def _parse_files(
        self,
        sales_bytes, sales_filename,
        purchase_bytes, purchase_filename,
        extra_files, our_gstin, period,
    ) -> tuple[list, int, list]:
        all_invoices = []
        files_parsed = 0
        parse_errors = []

        if sales_bytes and sales_filename:
            try:
                inv = parse_any_file(sales_bytes, filename=sales_filename,
                                     invoice_type="sale", our_gstin=our_gstin, period=period)
                all_invoices.extend(inv)
                files_parsed += 1
                logger.info(f"Sales: {len(inv)} invoices from {sales_filename}")
            except Exception as e:
                parse_errors.append(f"Sales ({sales_filename}): {e}")

        if purchase_bytes and purchase_filename:
            try:
                inv = parse_any_file(purchase_bytes, filename=purchase_filename,
                                     invoice_type="purchase", our_gstin=our_gstin, period=period)
                all_invoices.extend(inv)
                files_parsed += 1
                logger.info(f"Purchase: {len(inv)} invoices from {purchase_filename}")
            except Exception as e:
                parse_errors.append(f"Purchase ({purchase_filename}): {e}")

        for f_bytes, f_name in extra_files:
            try:
                fname_lower = f_name.lower()
                if any(k in fname_lower for k in ["sale", "gstr1", "gstr-1", "outward"]):
                    inv_type = "sale"
                elif any(k in fname_lower for k in ["purchase", "gstr2", "gstr-2", "inward", "2b"]):
                    inv_type = "purchase"
                else:
                    inv_type = "purchase"
                inv = parse_any_file(f_bytes, filename=f_name,
                                     invoice_type=inv_type, our_gstin=our_gstin, period=period)
                all_invoices.extend(inv)
                files_parsed += 1
            except Exception as e:
                parse_errors.append(f"{f_name}: {e}")

        return all_invoices, files_parsed, parse_errors

    def _build_record(
        self, audit_id, gstin_masked, period, language, sector,
        client_id, client_name, all_invoices, score_result,
        issues_json, itc_at_risk, itc_blocked,
        critical_count, high_count, medium_count, low_count,
        notice_sim,
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
            "issues_json":            issues_json,
            "itc_at_risk":            round(itc_at_risk, 2),
            "itc_blocked":            round(itc_blocked, 2),
            "itc_eligible":           0.0,
            "itc_summary": {
                "at_risk":      round(itc_at_risk, 2),
                "blocked":      round(itc_blocked, 2),
                "total_impact": round(itc_at_risk + itc_blocked, 2),
            },
            "critical_count":     critical_count,
            "high_count":         high_count,
            "medium_count":       medium_count,
            "low_count":          low_count,
            "notice_probability": notice_sim["probability"],
            "notice_risk_level":  notice_sim["risk_level"],
            "notice_simulation": {
                "probability":      notice_sim["probability"],
                "risk_level":       notice_sim["risk_level"],
                "risk_message":     notice_sim["risk_message"],
                "risk_areas":       notice_sim["risk_areas"],
                "possible_notices": notice_sim["possible_notices"],
                "what_if_fix_all":  notice_sim["what_if_fix_all"],
                "recommendations":  notice_sim["recommendations"][:5],
            },
        }

    def _generate_pdf(
        self, audit_id, gstin_masked, period, language,
        score_result, all_invoices, issues,
        itc_at_risk, itc_blocked,
        critical_count, high_count, medium_count, low_count,
        client_name,
    ) -> Optional[bytes]:
        try:
            audit_obj = AuditResponse(
                audit_id              = audit_id,
                client_gstin_masked   = gstin_masked,
                period                = period,
                language              = language,
                compliance_score      = score_result.score,
                risk_level            = score_result.risk_level,
                risk_level_translated = score_result.risk_level,
                total_invoices        = len(all_invoices),
                itc_summary           = ITCSummary(
                    at_risk  = itc_at_risk,
                    blocked  = itc_blocked,
                    total    = itc_at_risk + itc_blocked,
                ),
                issues         = issues,
                critical_count = critical_count,
                high_count     = high_count,
                medium_count   = medium_count,
                low_count      = low_count,
                created_at     = datetime.now(timezone.utc).isoformat(),
            )
            pdf_bytes = generate_pdf(
                audit_obj,
                ca_name     = self.deps.ca_name,
                client_name = client_name or "Client",
                lang        = language,
            )
            logger.info(f"PDF generated: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.error(f"PDF generation failed (non-fatal): {e}", exc_info=True)
            return None

    def _send_emails(
        self, score_result, notice_sim, issues, client_id,
        client_name, our_gstin, period, audit_id,
        itc_at_risk, critical_count, pdf_bytes,
    ) -> None:
        try:
            ca_email = self.deps.ca_email
            ca_name  = self.deps.ca_name

            if ca_email:
                sent = send_audit_complete_to_ca(
                    ca_email      = ca_email,
                    ca_name       = ca_name,
                    client_name   = client_name or "Client",
                    client_gstin  = our_gstin,
                    period        = period,
                    score         = score_result.score,
                    risk_level    = score_result.risk_level,
                    issues_count  = len(issues),
                    critical_count= critical_count,
                    itc_at_risk   = float(itc_at_risk),
                    notice_prob   = notice_sim.get("probability", 0),
                    audit_id      = audit_id,
                    pdf_content   = pdf_bytes,
                )
                logger.info(f"CA email {'sent' if sent else 'failed'} → {ca_email}")

            # High risk alert
            if ca_email and notice_sim.get("probability", 0) >= 50:
                send_high_risk_alert(
                    ca_email    = ca_email,
                    ca_name     = ca_name,
                    client_name = client_name or "Client",
                    score       = score_result.score,
                    notice_prob = notice_sim.get("probability", 0),
                    issues      = [i.dict() for i in issues if i.severity.value == "CRITICAL"],
                )

            # Client email
            if client_id:
                contact = self.deps.client_repo.get_contact(client_id, self.deps.ca_id)
                if contact:
                    client_email = self._clean_email(contact.get("email"))
                    if client_email and client_email != ca_email:
                        send_audit_complete_to_ca(
                            ca_email      = client_email,
                            ca_name       = contact.get("contact_person") or client_name or "Sir/Madam",
                            client_name   = client_name or "Your Business",
                            client_gstin  = our_gstin,
                            period        = period,
                            score         = score_result.score,
                            risk_level    = score_result.risk_level,
                            issues_count  = len(issues),
                            critical_count= critical_count,
                            itc_at_risk   = float(itc_at_risk),
                            notice_prob   = notice_sim.get("probability", 0),
                            audit_id      = audit_id,
                            pdf_content   = pdf_bytes,
                        )

        except Exception as e:
            logger.warning(f"Email sending failed (non-fatal): {e}", exc_info=True)

    @staticmethod
    def _safe_amount(issue) -> float:
        for attr in ("taxable_value", "amount", "taxable_amount", "itc_at_risk"):
            val = getattr(issue, attr, None)
            if val is not None and val != 0:
                return float(val)
        return 0.0

    @staticmethod
    def _clean_email(email: Optional[str]) -> Optional[str]:
        if not email:
            return None
        email = email.strip()
        if "@placeholder" in email or "auditai.app" in email or "@" not in email:
            return None
        return email