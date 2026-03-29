"""
services/email_service.py
--------------------------
Fixes:
  1. send_client_welcome() — naya function, client registration pe bheja jata hai
  2. send_audit_complete_to_ca() — same as before (CA + Client dono ko audit report)
  3. send_high_risk_alert() — same as before
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

BRAND_BLUE   = "#2563eb"
BRAND_DARK   = "#1e3a5f"
BRAND_GREEN  = "#16a34a"
BRAND_RED    = "#dc2626"
BRAND_ORANGE = "#d97706"


# ── SMTP Helper ───────────────────────────────────────────────
def _send(to: str, subject: str, html: str, pdf_content: bytes = None, filename: str = "report.pdf") -> bool:
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

        logger.info(f"✅ Email sent successfully to {to}")
        return True
    except Exception as e:
        logger.error(f"❌ SMTP failed for {to}: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# 1. CLIENT WELCOME EMAIL — Registration pe bheja jata hai
# ══════════════════════════════════════════════════════════════
def send_client_welcome(
    client_email: str,
    client_name:  str,
    ca_name:      str,
    ca_email:     str,
    gstin_masked: str,
) -> bool:
    """
    Jab CA kisi client ko add karta hai ya email update karta hai,
    tab client ko ye welcome email bheja jata hai.
    """
    subject = f"✅ You've been registered on AuditAI — {client_name}"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #f8fafc; padding: 20px; color: #334155;">
      <div style="max-width: 600px; margin: auto; background: white; border-radius: 12px;
                  border: 1px solid #e2e8f0; overflow: hidden;">

        <!-- Header -->
        <div style="background: {BRAND_BLUE}; color: white; padding: 28px; text-align: center;">
          <h1 style="margin: 0; font-size: 22px;">🛡️ AuditAI</h1>
          <p style="margin: 6px 0 0; font-size: 13px; opacity: 0.85;">Smart GST Compliance</p>
        </div>

        <!-- Body -->
        <div style="padding: 30px;">
          <h2 style="color: {BRAND_DARK}; margin-top: 0;">Welcome, {client_name}! 👋</h2>

          <p>Your GST compliance is now being managed by <b>{ca_name}</b> using AuditAI.</p>

          <div style="background: #f1f5f9; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-size: 13px; color: #64748b;">YOUR ACCOUNT DETAILS</p>
            <p style="margin: 4px 0;"><b>Business Name:</b> {client_name}</p>
            <p style="margin: 4px 0;"><b>GSTIN:</b> {gstin_masked}</p>
            <p style="margin: 4px 0;"><b>Managed By:</b> {ca_name} ({ca_email})</p>
          </div>

          <p><b>What happens next?</b></p>
          <ul style="color: #475569; line-height: 1.8;">
            <li>Your CA will run monthly GST audits on your data</li>
            <li>You'll receive audit reports with compliance scores</li>
            <li>Any GST issues will be flagged with step-by-step fix guides</li>
            <li>Notice probability will be calculated to keep you safe</li>
          </ul>

          <p style="color: #64748b; font-size: 13px; margin-top: 25px;">
            If you have any questions, contact your CA at
            <a href="mailto:{ca_email}" style="color: {BRAND_BLUE};">{ca_email}</a>
          </p>

          <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 25px 0;">
          <p style="font-size: 11px; color: #94a3b8; text-align: center;">
            This email was sent by AuditAI on behalf of {ca_name}.<br>
            You are receiving this because your CA registered your business on AuditAI.
          </p>
        </div>
      </div>
    </body>
    </html>
    """
    return _send(client_email, subject, html)


# ══════════════════════════════════════════════════════════════
# 2. AUDIT COMPLETE EMAIL — CA + Client dono ko bheja jata hai
# ══════════════════════════════════════════════════════════════
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
    is_client:     bool  = False,   # True hoga to client version bheja jayega
) -> bool:
    """
    CA aur Client dono ko audit complete email bheja jata hai.
    is_client=True hone pe subject aur tone thoda alag hoga.
    """
    score_color = BRAND_RED if score < 50 else (BRAND_ORANGE if score < 75 else BRAND_GREEN)
    risk_color  = BRAND_RED if risk_level.upper() in ("CRITICAL", "HIGH") else BRAND_GREEN

    if is_client:
        subject     = f"📊 Your GST Audit Report — {period} | Score: {score}/100"
        greeting    = f"Dear <b>{client_name}</b>,"
        intro       = f"Your GST audit for <b>{period}</b> has been completed by your CA <b>{ca_name}</b>."
    else:
        subject     = f"✅ GST Audit Complete — {client_name} | Score: {score}/100"
        greeting    = f"Hi <b>{ca_name}</b>,"
        intro       = f"The GST audit for <b>{client_name}</b> ({client_gstin}) for period <b>{period}</b> is complete."

    clean_period = period.replace("-", "_") if period else "report"
    filename     = f"GST_Audit_{client_name.replace(' ', '_')}_{clean_period}.pdf"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #f8fafc; padding: 20px; color: #334155;">
      <div style="max-width: 600px; margin: auto; background: white; border-radius: 12px;
                  border: 1px solid #e2e8f0; overflow: hidden;">

        <!-- Header -->
        <div style="background: {BRAND_DARK}; color: white; padding: 28px; text-align: center;">
          <h1 style="margin: 0; font-size: 22px;">🛡️ AuditAI Report</h1>
          <p style="margin: 6px 0 0; font-size: 13px; opacity: 0.75;">{client_name} · {period}</p>
        </div>

        <!-- Body -->
        <div style="padding: 30px;">
          <p style="margin-top: 0;">{greeting}</p>
          <p>{intro}</p>

          <!-- Score Box -->
          <div style="background: #f1f5f9; border-radius: 10px; padding: 25px;
                      text-align: center; margin: 20px 0;">
            <p style="margin: 0; font-size: 12px; color: #64748b; text-transform: uppercase;
                      letter-spacing: 1px;">Compliance Score</p>
            <h2 style="margin: 8px 0; font-size: 52px; color: {score_color}; line-height: 1;">
              {score}<span style="font-size: 24px;">/100</span>
            </h2>
            <span style="background: {risk_color}; color: white; padding: 4px 14px;
                         border-radius: 20px; font-size: 13px; font-weight: bold;">
              {risk_level.upper()} RISK
            </span>
          </div>

          <!-- Stats -->
          <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr>
              <td style="padding: 10px; background: #fef2f2; border-radius: 8px; text-align: center; width: 25%;">
                <p style="margin: 0; font-size: 22px; font-weight: bold; color: {BRAND_RED};">{issues_count}</p>
                <p style="margin: 4px 0 0; font-size: 11px; color: #64748b;">Total Issues</p>
              </td>
              <td style="width: 4%;"></td>
              <td style="padding: 10px; background: #fff1f2; border-radius: 8px; text-align: center; width: 25%;">
                <p style="margin: 0; font-size: 22px; font-weight: bold; color: {BRAND_RED};">{critical_count}</p>
                <p style="margin: 4px 0 0; font-size: 11px; color: #64748b;">Critical</p>
              </td>
              <td style="width: 4%;"></td>
              <td style="padding: 10px; background: #fff7ed; border-radius: 8px; text-align: center; width: 25%;">
                <p style="margin: 0; font-size: 22px; font-weight: bold; color: {BRAND_ORANGE};">
                  ₹{itc_at_risk:,.0f}
                </p>
                <p style="margin: 4px 0 0; font-size: 11px; color: #64748b;">ITC at Risk</p>
              </td>
              <td style="width: 4%;"></td>
              <td style="padding: 10px; background: #fef2f2; border-radius: 8px; text-align: center; width: 25%;">
                <p style="margin: 0; font-size: 22px; font-weight: bold; color: {BRAND_RED};">{notice_prob}%</p>
                <p style="margin: 4px 0 0; font-size: 11px; color: #64748b;">Notice Risk</p>
              </td>
            </tr>
          </table>

          {"<p>📎 <b>Detailed PDF report is attached</b> with issue-wise fix steps.</p>" if pdf_content else ""}

          <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 25px 0;">
          <p style="font-size: 11px; color: #94a3b8; text-align: center;">
            Audit ID: {audit_id}<br>
            Powered by AuditAI — Smart GST Compliance
          </p>
        </div>
      </div>
    </body>
    </html>
    """
    return _send(ca_email, subject, html, pdf_content, filename)


# ══════════════════════════════════════════════════════════════
# 3. HIGH RISK ALERT — 50%+ notice probability pe
# ══════════════════════════════════════════════════════════════
def send_high_risk_alert(
    ca_email:     str,
    ca_name:      str,
    client_name:  str,
    score:        int,
    notice_prob:  int,
    issues:       list,
) -> bool:
    subject = f"🚨 URGENT: High GST Notice Risk — {client_name} ({notice_prob}%)"

    issues_html = "".join([
        f"<li style='margin-bottom: 6px;'>❌ <b>{i.get('issue_type', 'Issue').replace('_', ' ').title()}</b>"
        f" — Invoice: {i.get('invoice_number', 'N/A')}</li>"
        for i in issues[:5]
    ]) or "<li>Multiple compliance issues detected</li>"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #f8fafc; padding: 20px; color: #334155;">
      <div style="max-width: 600px; margin: auto; background: white; border-radius: 12px;
                  border: 2px solid {BRAND_RED}; overflow: hidden;">

        <div style="background: {BRAND_RED}; color: white; padding: 20px; text-align: center;">
          <h2 style="margin: 0;">⚠️ High GST Notice Risk Detected</h2>
        </div>

        <div style="padding: 25px;">
          <p>Hi <b>{ca_name}</b>,</p>
          <p>
            The latest audit for <b>{client_name}</b> shows a
            <b style="color: {BRAND_RED};">{notice_prob}% GST notice probability</b>
            with a compliance score of <b>{score}/100</b>.
          </p>

          <p><b>Top Critical Issues:</b></p>
          <ul style="line-height: 1.8; color: #475569;">{issues_html}</ul>

          <div style="background: #fff1f2; border: 1px solid #fecaca; border-radius: 8px;
                      padding: 15px; margin: 20px 0;">
            <p style="margin: 0; font-weight: bold; color: {BRAND_RED};">
              ⚡ Immediate action recommended to avoid GST department notice.
            </p>
          </div>

          <p>Please review the full audit report and take corrective action.</p>

          <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;">
          <p style="font-size: 11px; color: #94a3b8; text-align: center;">
            AuditAI — Smart GST Compliance
          </p>
        </div>
      </div>
    </body>
    </html>
    """
    return _send(ca_email, subject, html)