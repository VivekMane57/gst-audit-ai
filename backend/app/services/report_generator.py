"""
services/report_generator.py
-----------------------------
Audit report PDF generate karo — ReportLab se.
EN / HI / MR support.
"""
import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import logging

from app.models.audit import AuditResponse
from app.models.issue import Severity

logger = logging.getLogger(__name__)

# ── Colors ────────────────────────────────────────────────────
DARK      = colors.HexColor("#0D1B2A")
BLUE      = colors.HexColor("#1565C0")
LIGHT_BLUE = colors.HexColor("#E3F2FD")
GREEN     = colors.HexColor("#2E7D32")
RED       = colors.HexColor("#B71C1C")
ORANGE    = colors.HexColor("#E65100")
GREY      = colors.HexColor("#37474F")
LIGHT_GREY = colors.HexColor("#F5F5F5")
WHITE     = colors.white
MID_GREY  = colors.HexColor("#CFD8DC")

# ── Risk colors ───────────────────────────────────────────────
RISK_COLORS = {
    "LOW":      GREEN,
    "MEDIUM":   ORANGE,
    "HIGH":     RED,
    "CRITICAL": colors.HexColor("#4A0000"),
}

SEVERITY_COLORS = {
    Severity.CRITICAL: colors.HexColor("#FFEBEE"),
    Severity.HIGH:     colors.HexColor("#FFF3E0"),
    Severity.MEDIUM:   colors.HexColor("#FFFDE7"),
    Severity.LOW:      LIGHT_GREY,
}

# ── Labels by language ────────────────────────────────────────
LABELS = {
    "en": {
        "title":       "GST Audit Report",
        "period":      "Period",
        "gstin":       "GSTIN",
        "score":       "Compliance Score",
        "risk":        "Risk Level",
        "invoices":    "Total Invoices Scanned",
        "issues":      "Issues Found",
        "itc_at_risk": "ITC at Risk",
        "fix":         "Fix Steps",
        "legal":       "Legal Reference",
        "penalty":     "Penalty Risk",
        "disclaimer":  (
            "DISCLAIMER: This report is for internal review only. "
            "Verify with a qualified CA before filing. "
            "This is not legal advice. "
            "GST Audit AI is not liable for any penalty."
        ),
        "generated":   "Generated",
        "critical":    "CRITICAL",
        "high":        "HIGH",
        "medium":      "MEDIUM",
        "low":         "LOW",
    },
    "hi": {
        "title":       "GST ऑडिट रिपोर्ट",
        "period":      "अवधि",
        "gstin":       "GSTIN",
        "score":       "अनुपालन स्कोर",
        "risk":        "जोखिम स्तर",
        "invoices":    "कुल इनवॉइस जांचे",
        "issues":      "समस्याएं मिलीं",
        "itc_at_risk": "जोखिम में ITC",
        "fix":         "सुधार के कदम",
        "legal":       "कानूनी संदर्भ",
        "penalty":     "जुर्माना जोखिम",
        "disclaimer":  (
            "अस्वीकरण: यह रिपोर्ट केवल आंतरिक समीक्षा के लिए है। "
            "फाइलिंग से पहले योग्य CA से सत्यापित करें। "
            "यह कानूनी सलाह नहीं है।"
        ),
        "generated":   "तैयार किया",
        "critical":    "गंभीर",
        "high":        "उच्च",
        "medium":      "मध्यम",
        "low":         "कम",
    },
    "mr": {
        "title":       "GST ऑडिट अहवाल",
        "period":      "कालावधी",
        "gstin":       "GSTIN",
        "score":       "अनुपालन स्कोर",
        "risk":        "धोका पातळी",
        "invoices":    "एकूण बीजके तपासली",
        "issues":      "समस्या आढळल्या",
        "itc_at_risk": "धोक्यातील ITC",
        "fix":         "सुधारणा पायऱ्या",
        "legal":       "कायदेशीर संदर्भ",
        "penalty":     "दंड धोका",
        "disclaimer":  (
            "अस्वीकरण: हा अहवाल केवळ अंतर्गत पुनरावलोकनासाठी आहे. "
            "दाखल करण्यापूर्वी पात्र CA कडून सत्यापित करा. "
            "हा कायदेशीर सल्ला नाही."
        ),
        "generated":   "तयार केले",
        "critical":    "गंभीर",
        "high":        "उच्च",
        "medium":      "मध्यम",
        "low":         "कमी",
    },
}


def _lbl(key: str, lang: str) -> str:
    return LABELS.get(lang, LABELS["en"]).get(key, key)


def generate_pdf(
    audit: AuditResponse,
    ca_name: str = "CA",
    client_name: str = "Client",
    lang: str = "en",
) -> bytes:
    """
    Audit report PDF generate karo.
    Returns PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )

    story = []
    L = lambda k: _lbl(k, lang)

    # ── Header ────────────────────────────────────────────────
    header_data = [[
        Paragraph(
            f"<b>{L('title')}</b>",
            ParagraphStyle("H", fontSize=16, textColor=WHITE,
                           fontName="Helvetica-Bold", alignment=TA_LEFT)
        ),
        Paragraph(
            f"GST Audit AI",
            ParagraphStyle("HR", fontSize=10, textColor=colors.HexColor("#90CAF9"),
                           alignment=TA_RIGHT)
        ),
    ]]
    header = Table(header_data, colWidths=[130*mm, 50*mm])
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(header)
    story.append(Spacer(1, 5*mm))

    # ── Meta info ─────────────────────────────────────────────
    risk_color = RISK_COLORS.get(audit.risk_level, GREY)
    meta_data = [
        [L("gstin"),    audit.client_gstin_masked,
         L("score"),    str(audit.compliance_score) + " / 100"],
        [L("period"),   audit.period,
         L("risk"),     audit.risk_level_translated],
        [L("invoices"), str(audit.total_invoices),
         L("itc_at_risk"), f"Rs.{audit.itc_summary.at_risk:,.2f}"],
        ["CA",          ca_name,
         L("issues"),   str(len(audit.issues))],
    ]
    meta = Table(meta_data, colWidths=[35*mm, 60*mm, 40*mm, 45*mm])
    meta.setStyle(TableStyle([
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (0,0), (2,-1), "Helvetica-Bold"),
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT_BLUE),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [LIGHT_BLUE, WHITE, LIGHT_BLUE, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.4, MID_GREY),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("TEXTCOLOR",     (3,1), (3,1), risk_color),
        ("FONTNAME",      (3,1), (3,1), "Helvetica-Bold"),
    ]))
    story.append(meta)
    story.append(Spacer(1, 6*mm))

    # ── Issues ────────────────────────────────────────────────
    if audit.issues:
        story.append(Paragraph(
            f"<b>{L('issues')} ({len(audit.issues)})</b>",
            ParagraphStyle("SH", fontSize=11, textColor=DARK,
                           fontName="Helvetica-Bold", spaceAfter=4)
        ))
        story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE))
        story.append(Spacer(1, 3*mm))

        for i, issue in enumerate(audit.issues, 1):
            sev_color = SEVERITY_COLORS.get(issue.severity, LIGHT_GREY)
            sev_label = L(issue.severity.value.lower())

            # Issue header
            ih_data = [[
                Paragraph(
                    f"<b>#{i} — {issue.invoice_number}</b>  "
                    f"[{sev_label}]",
                    ParagraphStyle("IH", fontSize=9.5, textColor=WHITE,
                                   fontName="Helvetica-Bold")
                ),
                Paragraph(
                    f"ITC Risk: Rs.{issue.itc_at_risk:,.2f}",
                    ParagraphStyle("IR", fontSize=9, textColor=colors.HexColor("#FFE082"),
                                   alignment=TA_RIGHT)
                ),
            ]]
            ih_bg = RISK_COLORS.get(issue.severity.value, GREY)
            ih = Table(ih_data, colWidths=[120*mm, 60*mm])
            ih.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), ih_bg),
                ("TOPPADDING",    (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("LEFTPADDING",   (0,0), (-1,-1), 10),
                ("RIGHTPADDING",  (0,0), (-1,-1), 8),
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ]))
            story.append(ih)

            # Problem text
            problem = issue.get_problem(lang)
            body_data = [
                [Paragraph(problem,
                           ParagraphStyle("PB", fontSize=9, textColor=DARK,
                                          leading=13))],
                [Paragraph(
                    f"<b>{L('legal')}:</b> {issue.legal_ref}",
                    ParagraphStyle("LR", fontSize=8.5, textColor=GREY,
                                   fontName="Helvetica-Oblique", leading=12)
                )],
            ]
            if issue.penalty_risk:
                body_data.append([
                    Paragraph(
                        f"<b>{L('penalty')}:</b> {issue.penalty_risk}",
                        ParagraphStyle("PR", fontSize=8.5, textColor=RED, leading=12)
                    )
                ])

            # Fix steps
            fix_text = "<br/>".join(
                f"• {step}" for step in issue.fix_steps
            )
            body_data.append([
                Paragraph(
                    f"<b>{L('fix')}:</b><br/>{fix_text}",
                    ParagraphStyle("FS", fontSize=8.5, textColor=GREEN,
                                   leading=13)
                )
            ])

            body = Table(body_data, colWidths=[180*mm])
            body.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), sev_color),
                ("TOPPADDING",    (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                ("LEFTPADDING",   (0,0), (-1,-1), 10),
                ("RIGHTPADDING",  (0,0), (-1,-1), 8),
                ("LINEBELOW",     (0,-1), (-1,-1), 0.3, MID_GREY),
            ]))
            story.append(body)
            story.append(Spacer(1, 3*mm))

    else:
        story.append(Paragraph(
            "✅ No issues found. Excellent compliance!",
            ParagraphStyle("OK", fontSize=11, textColor=GREEN,
                           fontName="Helvetica-Bold")
        ))

    story.append(Spacer(1, 5*mm))

    # ── ITC Summary ───────────────────────────────────────────
    itc_data = [
        ["ITC Summary", "Amount"],
        ["At Risk", f"Rs.{audit.itc_summary.at_risk:,.2f}"],
        ["Blocked", f"Rs.{audit.itc_summary.blocked:,.2f}"],
        ["Total Impact", f"Rs.{audit.itc_summary.total:,.2f}"],
    ]
    itc = Table(itc_data, colWidths=[120*mm, 60*mm])
    itc.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT_GREY, colors.HexColor("#FFEBEE")]),
        ("GRID",          (0,0), (-1,-1), 0.4, MID_GREY),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("ALIGN",         (1,0), (1,-1), "RIGHT"),
        ("FONTNAME",      (0,-1), (-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",     (0,-1), (-1,-1), RED),
    ]))
    story.append(itc)
    story.append(Spacer(1, 6*mm))

    # ── Disclaimer ────────────────────────────────────────────
    disclaimer_tbl = Table([[
        Paragraph(
            L("disclaimer"),
            ParagraphStyle("DIS", fontSize=7.5, textColor=GREY,
                           fontName="Helvetica-Oblique", leading=11)
        )
    ]], colWidths=[180*mm])
    disclaimer_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), LIGHT_GREY),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("LINEBEFORE",  (0,0), (0,-1), 3, ORANGE),
    ]))
    story.append(disclaimer_tbl)

    # ── Footer ────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 2*mm))
    now = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    story.append(Paragraph(
        f"{L('generated')}: {now}  |  Audit ID: {audit.audit_id}  |  gstauditai.com",
        ParagraphStyle("FT", fontSize=7, textColor=GREY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()