"""
services/email_service.py  (Enhanced)
---------------------------------------
Changes from previous version:
  1. send_audit_complete_to_ca() — now accepts:
     - top_risk_reasons: List[str]  → shown in email body
     - estimated_penalty_exposure: float → shown prominently
  2. send_high_risk_alert() — now accepts same new params,
     shows top 3 risk reasons + penalty in alert
  3. _send() — unchanged
  4. send_client_welcome() — unchanged
  5. All new params are Optional with defaults — backward compatible
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

BRAND_BLUE   = "#2563eb"
BRAND_DARK   = "#1e3a5f"
BRAND_GREEN  = "#16a34a"
BRAND_RED    = "#dc2626"
BRAND_ORANGE = "#d97706"


# ── SMTP Helper (unchanged) ───────────────────────────────────
def _send(
    to:          str,
    subject:     str,
    html:        str,
    pdf_content: bytes = None,
    filename:    str   = "report.pdf",
) -> bool:
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not set in .env")
        return False
    try:
        msg             = MIMEMultipart()
        msg["From"]     = smtp_from
        msg["To"]       = to
        msg["Subject"]  = subject
        msg.attach(MIMEText(html, "html"))
        if pdf_content:
            part = MIMEApplication(pdf_content, Name=filename)
            part["Content-Disposition"] = f'attachment; filename="{filename}"'
            msg.attach(part)
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info(f"✅ Email sent → {to}")
        return True
    except Exception as e:
        logger.error(f"❌ SMTP failed for {to}: {e}")
        return False


# ── Welcome email (unchanged) ─────────────────────────────────
def send_client_welcome(
    client_email: str,
    client_name:  str,
    ca_name:      str,
    ca_email:     str,
    gstin_masked: str,
) -> bool:
    subject = f"✅ You've been registered on AuditAI — {client_name}"
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px;color:#334155;">
    <div style="max-width:600px;margin:auto;background:white;border-radius:12px;border:1px solid #e2e8f0;overflow:hidden;">
      <div style="background:{BRAND_BLUE};color:white;padding:28px;text-align:center;">
        <h1 style="margin:0;font-size:22px;">🛡️ AuditAI</h1>
        <p style="margin:6px 0 0;font-size:13px;opacity:.85;">Smart GST Compliance</p>
      </div>
      <div style="padding:30px;">
        <h2 style="color:{BRAND_DARK};margin-top:0;">Welcome, {client_name}! 👋</h2>
        <p>Your GST compliance is now managed by <b>{ca_name}</b> using AuditAI.</p>
        <div style="background:#f1f5f9;border-radius:8px;padding:20px;margin:20px 0;">
          <p style="margin:0 0 8px;font-size:13px;color:#64748b;">YOUR ACCOUNT DETAILS</p>
          <p style="margin:4px 0;"><b>Business Name:</b> {client_name}</p>
          <p style="margin:4px 0;"><b>GSTIN:</b> {gstin_masked}</p>
          <p style="margin:4px 0;"><b>Managed By:</b> {ca_name} ({ca_email})</p>
        </div>
        <p><b>What happens next?</b></p>
        <ul style="color:#475569;line-height:1.8;">
          <li>Monthly GST audits on your data</li>
          <li>Audit reports with compliance scores</li>
          <li>GST issues flagged with fix guides</li>
          <li>Notice probability calculated to keep you safe</li>
        </ul>
        <hr style="border:0;border-top:1px solid #e2e8f0;margin:25px 0;">
        <p style="font-size:11px;color:#94a3b8;text-align:center;">
          Sent by AuditAI on behalf of {ca_name}.
        </p>
      </div>
    </div>
    </body></html>
    """
    return _send(client_email, subject, html)


# ── Audit complete email (Enhanced) ──────────────────────────
def send_audit_complete_to_ca(
    ca_email:      str,
    ca_name:       str,
    client_name:   str,
    client_gstin:  str,
    period:        str,
    score:         int,
    risk_level:    str,
    issues_count:  int,
    critical_count: int,
    itc_at_risk:   float,
    notice_prob:   int,
    audit_id:      str,
    pdf_content:   bytes = None,
    is_client:     bool  = False,
    # NEW optional params — backward compatible
    top_risk_reasons:           Optional[List[str]] = None,
    estimated_penalty_exposure: float               = 0.0,
) -> bool:
    score_color = BRAND_RED if score < 50 else (BRAND_ORANGE if score < 75 else BRAND_GREEN)
    risk_color  = BRAND_RED if risk_level.upper() in ("CRITICAL", "HIGH", "VERY_HIGH") else BRAND_GREEN

    if is_client:
        subject  = f"📊 Your GST Audit Report — {period} | Score: {score}/100"
        greeting = f"Dear <b>{client_name}</b>,"
        intro    = f"Your GST audit for <b>{period}</b> has been completed by your CA <b>{ca_name}</b>."
    else:
        subject  = f"✅ GST Audit Complete — {client_name} | Score: {score}/100"
        greeting = f"Hi <b>{ca_name}</b>,"
        intro    = f"The GST audit for <b>{client_name}</b> ({client_gstin}) for period <b>{period}</b> is complete."

    clean_period = period.replace("-", "_") if period else "report"
    filename     = f"GST_Audit_{client_name.replace(' ', '_')}_{clean_period}.pdf"

    # Build top risk reasons HTML
    top_reasons_html = ""
    if top_risk_reasons:
        items = "".join(f"<li style='margin-bottom:6px;color:#475569;'>⚠️ {r}</li>" for r in top_risk_reasons[:3])
        top_reasons_html = f"""
        <div style="margin:20px 0;">
          <p style="font-weight:bold;color:{BRAND_DARK};margin-bottom:10px;">🎯 Top Risk Reasons:</p>
          <ul style="padding-left:20px;line-height:1.8;">{items}</ul>
        </div>
        """

    # Penalty exposure block
    penalty_html = ""
    if estimated_penalty_exposure > 0:
        penalty_html = f"""
        <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:14px 16px;margin:15px 0;">
          <p style="margin:0;font-size:13px;color:{BRAND_ORANGE};">
            ⚡ <b>Estimated Penalty Exposure:</b>
            ₹{estimated_penalty_exposure:,.0f}
            <span style="font-size:11px;color:#92400e;"> (conservative estimate)</span>
          </p>
        </div>
        """

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px;color:#334155;">
    <div style="max-width:600px;margin:auto;background:white;border-radius:12px;
                border:1px solid #e2e8f0;overflow:hidden;">

      <div style="background:{BRAND_DARK};color:white;padding:28px;text-align:center;">
        <h1 style="margin:0;font-size:22px;">🛡️ AuditAI Report</h1>
        <p style="margin:6px 0 0;font-size:13px;opacity:.75;">{client_name} · {period}</p>
      </div>

      <div style="padding:30px;">
        <p style="margin-top:0;">{greeting}</p>
        <p>{intro}</p>

        <!-- Score Box -->
        <div style="background:#f1f5f9;border-radius:10px;padding:25px;
                    text-align:center;margin:20px 0;">
          <p style="margin:0;font-size:12px;color:#64748b;text-transform:uppercase;
                    letter-spacing:1px;">Compliance Score</p>
          <h2 style="margin:8px 0;font-size:52px;color:{score_color};line-height:1;">
            {score}<span style="font-size:24px;">/100</span>
          </h2>
          <span style="background:{risk_color};color:white;padding:4px 14px;
                       border-radius:20px;font-size:13px;font-weight:bold;">
            {risk_level.upper()} RISK
          </span>
        </div>

        <!-- Stats Grid -->
        <table style="width:100%;border-collapse:collapse;margin:15px 0;">
          <tr>
            <td style="padding:10px;background:#fef2f2;border-radius:8px;text-align:center;width:24%;">
              <p style="margin:0;font-size:22px;font-weight:bold;color:{BRAND_RED};">{issues_count}</p>
              <p style="margin:4px 0 0;font-size:11px;color:#64748b;">Total Issues</p>
            </td>
            <td style="width:2%;"></td>
            <td style="padding:10px;background:#fff1f2;border-radius:8px;text-align:center;width:24%;">
              <p style="margin:0;font-size:22px;font-weight:bold;color:{BRAND_RED};">{critical_count}</p>
              <p style="margin:4px 0 0;font-size:11px;color:#64748b;">Critical</p>
            </td>
            <td style="width:2%;"></td>
            <td style="padding:10px;background:#fff7ed;border-radius:8px;text-align:center;width:24%;">
              <p style="margin:0;font-size:22px;font-weight:bold;color:{BRAND_ORANGE};">
                ₹{itc_at_risk:,.0f}
              </p>
              <p style="margin:4px 0 0;font-size:11px;color:#64748b;">ITC at Risk</p>
            </td>
            <td style="width:2%;"></td>
            <td style="padding:10px;background:#fef2f2;border-radius:8px;text-align:center;width:24%;">
              <p style="margin:0;font-size:22px;font-weight:bold;color:{BRAND_RED};">{notice_prob}%</p>
              <p style="margin:4px 0 0;font-size:11px;color:#64748b;">Notice Risk</p>
            </td>
          </tr>
        </table>

        {top_reasons_html}
        {penalty_html}

        {"<p>📎 <b>Detailed PDF report attached</b> with issue-wise fix steps and legal references.</p>" if pdf_content else ""}

        <!-- CTA -->
        <div style="text-align:center;margin:25px 0;">
          <a href="https://app.auditai.in/reports/{audit_id}"
             style="background:{BRAND_BLUE};color:white;padding:12px 28px;
                    border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px;">
            View Full Report →
          </a>
        </div>

        <hr style="border:0;border-top:1px solid #e2e8f0;margin:25px 0;">
        <p style="font-size:11px;color:#94a3b8;text-align:center;">
          Audit ID: {audit_id}<br>Powered by AuditAI — Smart GST Compliance
        </p>
      </div>
    </div>
    </body></html>
    """
    return _send(ca_email, subject, html, pdf_content, filename)


# ── High risk alert (Enhanced) ────────────────────────────────
def send_high_risk_alert(
    ca_email:    str,
    ca_name:     str,
    client_name: str,
    score:       int,
    notice_prob: int,
    issues:      list,
    # NEW optional params — backward compatible
    top_risk_reasons:           Optional[List[str]] = None,
    estimated_penalty_exposure: float               = 0.0,
) -> bool:
    subject = f"🚨 URGENT: High GST Notice Risk — {client_name} ({notice_prob}%)"

    issues_html = "".join([
        f"<li style='margin-bottom:6px;'>❌ <b>{i.get('issue_type', i.get('type', 'Issue')).replace('_', ' ').title()}</b>"
        f" — Invoice: {i.get('invoice_number', i.get('invoice', 'N/A'))}"
        f"{(' | ₹' + str(int(i.get('itc_at_risk', 0))) + ' at risk') if i.get('itc_at_risk', 0) > 0 else ''}</li>"
        for i in issues[:5]
    ]) or "<li>Multiple compliance issues detected</li>"

    # Top risk reasons block
    reasons_html = ""
    if top_risk_reasons:
        items = "".join(f"<li style='color:#7f1d1d;margin-bottom:4px;'>{r}</li>" for r in top_risk_reasons[:3])
        reasons_html = f"""
        <div style="margin:15px 0;">
          <p style="font-weight:bold;color:#991b1b;">🎯 Main Risk Drivers:</p>
          <ul style="padding-left:20px;">{items}</ul>
        </div>
        """

    # Penalty block
    penalty_html = ""
    if estimated_penalty_exposure > 0:
        penalty_html = f"""
        <div style="background:#fff7ed;border:1px solid #fbbf24;border-radius:8px;
                    padding:12px 16px;margin:12px 0;">
          <p style="margin:0;font-size:14px;font-weight:bold;color:{BRAND_ORANGE};">
            ⚡ Estimated Penalty Exposure: ₹{estimated_penalty_exposure:,.0f}
          </p>
        </div>
        """

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px;color:#334155;">
    <div style="max-width:600px;margin:auto;background:white;border-radius:12px;
                border:2px solid {BRAND_RED};overflow:hidden;">
      <div style="background:{BRAND_RED};color:white;padding:20px;text-align:center;">
        <h2 style="margin:0;">⚠️ High GST Notice Risk Detected</h2>
      </div>
      <div style="padding:25px;">
        <p>Hi <b>{ca_name}</b>,</p>
        <p>The latest audit for <b>{client_name}</b> shows a
           <b style="color:{BRAND_RED};">{notice_prob}% GST notice probability</b>
           with compliance score <b>{score}/100</b>.</p>

        <p><b>Top Critical Issues:</b></p>
        <ul style="line-height:1.8;color:#475569;">{issues_html}</ul>

        {reasons_html}
        {penalty_html}

        <div style="background:#fff1f2;border:1px solid #fecaca;border-radius:8px;
                    padding:15px;margin:20px 0;">
          <p style="margin:0;font-weight:bold;color:{BRAND_RED};">
            ⚡ Immediate action recommended to prevent a GST department notice.
          </p>
        </div>

        <hr style="border:0;border-top:1px solid #e2e8f0;margin:20px 0;">
        <p style="font-size:11px;color:#94a3b8;text-align:center;">
          AuditAI — Smart GST Compliance
        </p>
      </div>
    </div>
    </body></html>
    """
    return _send(ca_email, subject, html)