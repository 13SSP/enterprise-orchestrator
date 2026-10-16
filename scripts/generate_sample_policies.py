"""
generate_sample_policies.py
Generates realistic enterprise sample policies in both Markdown (.md) and PDF (.pdf) formats,
plus sample invoices/receipts for Document AI testing.
All files are saved to: D:/AI Orchestrator/enterprise-orchestrator/enterprise_knowledge_base/
"""

import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent / "enterprise_knowledge_base"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------
# Numbered Canvas for Professional Footers ("Page X of Y")
# ------------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#718096"))
        
        # Header line & doc title
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, letter[1] - 40, letter[0] - 54, letter[1] - 40)
        self.drawString(54, letter[1] - 34, "cortex.ai Enterprise Knowledge Base — Confidential & Internal Use Only")

        # Footer line & page count
        self.line(54, 45, letter[0] - 54, 45)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 32, page_str)
        self.drawString(54, 32, "Google Cloud AI Builder Cup | Enterprise Orchestrator Reference Policy")
        self.restoreState()


# ------------------------------------------------------------------------------
# PDF Styling Helper
# ------------------------------------------------------------------------------
def get_pdf_styles():
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'DocH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=14,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=body_style,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'DocCallout',
        parent=body_style,
        fontName='Helvetica-Oblique',
        textColor=colors.HexColor("#1A202C"),
        backColor=colors.HexColor("#EDF2F7"),
        borderColor=colors.HexColor("#3182CE"),
        borderWidth=1,
        borderPadding=6,
        spaceBefore=8,
        spaceAfter=8
    )

    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'h1': h1_style,
        'h2': h2_style,
        'body': body_style,
        'bullet': bullet_style,
        'callout': callout_style
    }


# ==============================================================================
# 1. HR POLICY: Employee Handbook & Leave Entitlements
# ==============================================================================
HR_POLICY_MD = """# Global Enterprise HR Policy & Leave Entitlements Manual
**Document ID**: HR-POL-2026-v3  
**Effective Date**: January 1, 2026  
**Applicability**: All full-time, part-time, and contracted corporate employees  
**Owner**: People & Culture Operations  

---

## 1. Purpose & Philosophy
This document sets forth company-wide standards regarding paid time off (PTO), sick leaves, parental benefits, hybrid work schedules, and employee code of conduct. These policies ensure consistent, equitable treatment across all business units.

---

## 2. Paid Time Off (PTO) & Leave Allocations

### 2.1 Annual Vacation Leave
* **Full-Time Employees**: Accrue **20 working days** of paid vacation per calendar year (accrual rate of 1.66 days per completed calendar month).
* **Senior Leadership (Director+)**: Accrue **25 working days** of paid vacation per year.
* **Probationary Period**: Employees may utilize accrued PTO after completing 60 calendar days of service.

### 2.2 Year-End Carryover & Rollover Cap
* A maximum of **5 unused vacation days** may be rolled over into the subsequent calendar year.
* All carried-over days must be utilized prior to **March 31st** of the new year. Any carried-over days remaining beyond March 31st are forfeited without financial compensation unless mandated by local labor legislation.

### 2.3 Sick & Medical Leave
* Employees receive **10 paid medical/sick leave days** annually.
* Absences exceeding **3 consecutive calendar days** require an official medical practitioner note uploaded to the employee HR portal.
* Sick days do not roll over and are not compensable upon termination.

### 2.4 Paid Parental Leave
* **Primary Caregivers**: **16 weeks of 100% fully paid leave** following birth, adoption, or foster placement.
* **Secondary Caregivers**: **6 weeks of 100% fully paid leave**.
* Parental leave must be taken within 12 months following the qualifying life event.

---

## 3. Leave Request & Approval Workflow
1. **Advance Notice**: Vacation requests spanning more than 3 consecutive working days must be submitted through `cortex.ai` or the HRIS portal at least **10 business days** in advance.
2. **Approval Hierarchy**: Requests are routed to the employee's direct manager. Managers must approve or deny requests within 48 business hours.
3. **Blackout Periods**: Key quarterly financial close windows (last 3 business days of March, June, September, December) are restricted for Finance and Accounting teams.

---

## 4. Hybrid & Remote Work Framework
* **Hybrid Schedule**: Teams observe a **3/2 model** (3 days collaborative in-office, 2 days remote work).
* **Core Working Hours**: Core availability across all corporate teams is **10:00 AM to 4:00 PM** in the respective local time zone.
* **Remote Workspace Allowance**: A one-time ergonomic stipend of **$500 USD** is provided to new full-time hires for home office equipment.

---

## 5. Summary Leave Matrix

| Leave Category | Annual Allowance | Carryover Limit | Medical Cert Required? |
|---|---|---|---|
| **Vacation Leave** | 20 Days (25 for Director+) | Max 5 Days (Expires March 31) | No |
| **Sick Leave** | 10 Days | 0 Days (Use it or lose it) | Yes (after 3 days) |
| **Parental Leave** | 16 Weeks (Primary) / 6 Weeks (Secondary) | N/A | Yes (Proof of birth/adoption) |
| **Bereavement** | 5 Days (Immediate family) | 0 Days | Discretionary |
| **Jury Duty** | Up to 10 Days Paid | 0 Days | Court Summons Required |
"""

def build_hr_pdf():
    pdf_path = BASE_DIR / "HR_Employee_Handbook_and_Leave_Policy.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_pdf_styles()
    story = []

    story.append(Paragraph("Global HR Policy & Leave Entitlements Manual", styles['title']))
    story.append(Paragraph("Document ID: HR-POL-2026-v3 | Effective Date: January 1, 2026 | People & Culture", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=12))

    story.append(Paragraph("1. Executive Summary & Purpose", styles['h1']))
    story.append(Paragraph(
        "This manual sets forth corporate standards governing paid time off (PTO), sick leaves, parental benefits, hybrid work schedules, and core hours. These policies ensure consistent, compliant, and equitable treatment across all global departments.",
        styles['body']
    ))

    story.append(Paragraph("2. Paid Time Off (PTO) & Leave Entitlements", styles['h1']))
    story.append(Paragraph("<b>2.1 Vacation Leave:</b> Full-time employees accrue <b>20 working days</b> of paid vacation annually (1.66 days/month). Directors and above accrue 25 days.", styles['bullet']))
    story.append(Paragraph("<b>2.2 Rollover Limits:</b> A maximum of <b>5 unused vacation days</b> can roll over to the next year. Rolled-over days must be utilized before <b>March 31st</b> or be forfeited.", styles['bullet']))
    story.append(Paragraph("<b>2.3 Sick & Medical Leave:</b> 10 paid sick days per year. Absences exceeding 3 consecutive working days require an official medical practitioner note.", styles['bullet']))
    story.append(Paragraph("<b>2.4 Paid Parental Leave:</b> 16 weeks of 100% paid leave for primary caregivers; 6 weeks for secondary caregivers, eligible within 12 months of birth or adoption.", styles['bullet']))

    story.append(Paragraph("3. Hybrid & Remote Work Framework", styles['h1']))
    story.append(Paragraph(
        "Teams follow a <b>3/2 model</b> (3 days in-office, 2 days remote). Core collaboration hours are <b>10:00 AM to 4:00 PM local time</b>. A one-time ergonomic stipend of $500 USD is available for new hires.",
        styles['body']
    ))

    story.append(Paragraph("4. Summary Leave Entitlement Matrix", styles['h1']))
    
    table_data = [
        ["Leave Category", "Annual Allowance", "Carryover Limit", "Certification Req."],
        ["Vacation Leave", "20 Days (25 Director+)", "Max 5 Days (Expires Mar 31)", "Manager Approval"],
        ["Sick Leave", "10 Days Paid", "0 Days (No rollover)", "Yes (after 3 days)"],
        ["Parental Leave", "16 Weeks / 6 Weeks", "Take within 12 months", "Birth / Adoption Cert"],
        ["Bereavement", "5 Days Paid", "0 Days", "Discretionary"],
        ["Jury Duty", "Up to 10 Days Paid", "0 Days", "Court Summons"]
    ]
    t = Table(table_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.6*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    story.append(Paragraph(
        "<b>Important Compliance Notice:</b> Automated approval routing through cortex.ai AI Assistant enforces manager verification. Any leave balance discrepancies should be filed directly with People Operations via <code>hr@company.internal</code>.",
        styles['callout']
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


# ==============================================================================
# 2. FINANCE POLICY: Travel & Expense Reimbursement Policy
# ==============================================================================
FINANCE_POLICY_MD = """# Corporate Travel & Business Expense Reimbursement Policy
**Document ID**: FIN-EXP-2026-v2  
**Effective Date**: January 1, 2026  
**Audience**: All personnel incurring authorized business expenses  
**Owner**: Corporate Finance & Controller Office  

---

## 1. Overview & Scope
This policy defines reimbursable business expenses, per diem rates, travel booking parameters, receipt validation standards, and approval thresholds. Employees are expected to exercise prudent judgment and stewardship of company funds.

---

## 2. Daily Per Diem & Meal Allowances
Meals incurred during authorized business travel are reimbursed on an actual cost basis up to the following maximum caps:

* **Domestic Travel (Standard Cities)**: **$75.00 USD / day**
  - Breakfast: $15.00
  - Lunch: $25.00
  - Dinner: $35.00
* **Domestic Travel (High-Cost Metro Tier-1: NYC, SF, London, Tokyo)**: **$100.00 USD / day**
* **International Travel**: **$120.00 USD / day**
* **Alcohol Policy**: Alcoholic beverages are reimbursable only during authorized client entertainment dinners and must not exceed 25% of total food bill.

---

## 3. Lodging & Transportation Caps

### 3.1 Hotel Accommodation
* **Standard Metros**: Maximum room rate of **$200.00 USD / night** (excluding taxes).
* **Tier-1 Major Metros**: Maximum room rate of **$320.00 USD / night**.
* Bookings must be made via the enterprise corporate travel portal at least **14 calendar days** prior to travel.

### 3.2 Air Travel
* **Flights Under 6 Hours**: Economy Class / Main Cabin only.
* **Flights Over 6 Hours (Non-stop international)**: Premium Economy or Business Class permitted with Vice President pre-approval.

### 3.3 Ground Transportation
* Preferred providers: Standard rideshare (UberX, Lyft Standard), public transit, or airport train.
* Premium car categories (Uber Black, Luxury Rentals) are strictly non-reimbursable without prior written Director approval.

---

## 4. Receipt Requirements & Submission Window
* **Receipt Threshold**: Itemized receipts are **mandatory for all expenses exceeding $25.00 USD**.
* **Submission Deadline**: Expense reports must be submitted within **30 calendar days** from the transaction date. Submissions beyond 60 days will be rejected by Finance.
* **Non-Reimbursable Items**: Personal entertainment, hotel in-room movies, flight upgrades, traffic/parking citations, and airline lounge memberships.

---

## 5. Approval Matrix & Financial Ceilings

| Total Claim Amount | Required Approver Level | Processing SLA |
|---|---|---|
| **Up to $500.00 USD** | Direct Manager | 3 Business Days |
| **$500.01 – $2,500.00 USD** | Department Director | 5 Business Days |
| **Over $2,500.00 USD** | VP of Business Unit + Finance Controller | 7 Business Days |
"""

def build_finance_pdf():
    pdf_path = BASE_DIR / "Finance_and_Travel_Expense_Policy.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_pdf_styles()
    story = []

    story.append(Paragraph("Corporate Travel & Expense Reimbursement Policy", styles['title']))
    story.append(Paragraph("Document ID: FIN-EXP-2026-v2 | Effective Date: January 1, 2026 | Finance & Controller", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=12))

    story.append(Paragraph("1. Purpose & Core Principles", styles['h1']))
    story.append(Paragraph(
        "This policy defines allowable corporate expenditures, per diem meal allowances, hotel caps, receipt compliance, and financial approval hierarchies. Employees must act as responsible fiduciaries of corporate resources.",
        styles['body']
    ))

    story.append(Paragraph("2. Meal Allowances & Daily Per Diem Rates", styles['h1']))
    story.append(Paragraph("• <b>Domestic Travel (Standard):</b> $75.00/day (Breakfast: $15, Lunch: $25, Dinner: $35).", styles['bullet']))
    story.append(Paragraph("• <b>Tier-1 Metro Cities (NYC, SF, London, Tokyo, Singapore):</b> $100.00/day.", styles['bullet']))
    story.append(Paragraph("• <b>International Business Travel:</b> $120.00/day maximum.", styles['bullet']))
    story.append(Paragraph("• <b>Receipt Mandate:</b> Itemized receipts are required for all individual expenses exceeding <b>$25.00 USD</b>.", styles['bullet']))

    story.append(Paragraph("3. Lodging & Commercial Airfare Limits", styles['h1']))
    story.append(Paragraph("• <b>Hotels:</b> Max $200/night for standard cities; up to $320/night for Tier-1 metros.", styles['bullet']))
    story.append(Paragraph("• <b>Flights:</b> Economy class for all domestic routes under 6 hours. Business class allowed only for intercontinental flights >6 hours with VP approval.", styles['bullet']))
    story.append(Paragraph("• <b>Submission Timeline:</b> Expenses must be filed within <b>30 days</b> of occurrence.", styles['bullet']))

    story.append(Paragraph("4. Financial Approval Authority Matrix", styles['h1']))
    table_data = [
        ["Claim Amount Bracket", "Required Approval Authority", "Reimbursement SLA"],
        ["Up to $500.00 USD", "Direct Manager Sign-off", "3 Business Days"],
        ["$500.01 – $2,500.00 USD", "Department Director Approval", "5 Business Days"],
        ["Exceeding $2,500.00 USD", "Business Unit VP + Finance Controller", "7 Business Days"]
    ]
    t = Table(table_data, colWidths=[2.3*inch, 2.7*inch, 2.0*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    story.append(Paragraph(
        "<b>Document AI Automation Notice:</b> cortex.ai utilizes Google Cloud Document AI to automatically extract merchant, date, and tax amounts from uploaded PDF/image receipts. Altered or forged receipts result in disciplinary action.",
        styles['callout']
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


# ==============================================================================
# 3. IT & CYBERSECURITY POLICY: Data Classification & Access Control
# ==============================================================================
IT_SECURITY_POLICY_MD = """# Enterprise Cybersecurity, Data Classification & Identity Governance Policy
**Document ID**: SEC-POL-2026-v4  
**Effective Date**: January 1, 2026  
**Classification**: Internal / Confidential  
**Owner**: Chief Information Security Officer (CISO)  

---

## 1. Information Security Mandate
The security of corporate intellectual property, employee personal information (PII), and customer records is critical. All employees must follow strict Zero-Trust security rules when accessing corporate networks, databases, and generative AI interfaces.

---

## 2. Password & Multi-Factor Authentication (MFA)
* **MFA Requirement**: Hardware FIDO2 Security Keys or Google Authenticator MFA are **mandatory** on all corporate Single Sign-On (SSO) accounts. SMS-based 2FA is prohibited due to SIM-swap vulnerabilities.
* **Password Complexity**: Minimum 14 characters containing uppercase, lowercase, numbers, and symbols.
* **Session Timeout**: Corporate laptops lock automatically after **10 minutes** of inactivity.

---

## 3. Four-Tier Data Classification Matrix

| Classification Level | Definition & Examples | Handling & Protection Rules |
|---|---|---|
| **Level 1: Public** | Marketing brochures, public press releases, job postings. | No restrictions. |
| **Level 2: Internal** | Internal wikis, organizational charts, operational memos. | Authenticated corporate SSO required. |
| **Level 3: Confidential** | Customer contracts, vendor invoices, product source code. | Encryption in transit & at rest; access restricted to need-to-know. |
| **Level 4: Restricted** | Employee compensation, SSNs, financial ledgers, encryption keys. | Strict RBAC; two-layer approval; mandatory masking in AI outputs. |

---

## 4. Generative AI & LLM Usage Guardrails
1. **Model Armor Enforcement**: No employee may input Level 4 Restricted data (SSNs, raw credit cards, unreleased earnings) into unapproved public AI tools.
2. **Jailbreak & Prompt Injection**: Intentionally engineering prompts to bypass system guardrails, extract internal system instructions, or access unauthorized databases is considered a severe security violation.
3. **Auditability**: All queries processed via `cortex.ai` are logged with request timestamp, user identity, policy decisions, and output PII sanitization status.

---

## 5. Security Incident Severity Tiers & SLA Response Times

* **Critical (Sev-1)**: Active security breach, ransomware, or confirmed data exfiltration.
  - *Response Time*: **15 Minutes** (24/7/365 CISO emergency bridge).
* **High (Sev-2)**: Compromised employee credential, production service vulnerability, or malware detection.
  - *Response Time*: **1 Hour**.
* **Medium (Sev-3)**: Phishing email report, misconfigured non-production firewall rule.
  - *Response Time*: **4 Business Hours**.
* **Low (Sev-4)**: Routine permission inquiry, security audit question.
  - *Response Time*: **1 Business Day**.
"""

def build_it_security_pdf():
    pdf_path = BASE_DIR / "IT_Security_and_Data_Protection_Policy.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_pdf_styles()
    story = []

    story.append(Paragraph("Enterprise Cybersecurity & Data Governance Policy", styles['title']))
    story.append(Paragraph("Document ID: SEC-POL-2026-v4 | Effective Date: January 1, 2026 | Office of the CISO", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=12))

    story.append(Paragraph("1. Security Mandate & Zero-Trust Architecture", styles['h1']))
    story.append(Paragraph(
        "All corporate systems enforce Zero-Trust access: verify explicitly, enforce least privilege, and assume breach. Multi-Factor Authentication (MFA) via FIDO2 keys or Authenticator apps is mandatory for all employee accounts.",
        styles['body']
    ))

    story.append(Paragraph("2. Four-Tier Data Classification Matrix", styles['h1']))
    table_data = [
        ["Classification", "Definition & Examples", "Handling & AI Restrictions"],
        ["Public (L1)", "Press releases, careers site", "Unrestricted sharing"],
        ["Internal (L2)", "Internal wikis, project tickets", "Corporate SSO required"],
        ["Confidential (L3)", "Client contracts, source code", "Encrypted; restricted access"],
        ["Restricted (L4)", "Salaries, SSNs, financial ledgers", "Masked by Model Armor; Zero-Trust RBAC"]
    ]
    t = Table(table_data, colWidths=[1.8*inch, 2.5*inch, 2.7*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("3. Incident Response SLA Tiers", styles['h1']))
    story.append(Paragraph("• <b>Sev-1 (Critical):</b> Active breach or data leakage. SLA: <b>15 minutes</b> (24/7 bridge).", styles['bullet']))
    story.append(Paragraph("• <b>Sev-2 (High):</b> Compromised credentials or server compromise. SLA: <b>1 hour</b>.", styles['bullet']))
    story.append(Paragraph("• <b>Sev-3 (Medium):</b> Suspicious phishing attack or isolated malware. SLA: <b>4 business hours</b>.", styles['bullet']))

    story.append(Paragraph(
        "<b>Model Armor Protection Notice:</b> cortex.ai natively enforces Google Model Armor and regex filters to automatically block prompt injection attacks and redact Level 4 PII (Social Security numbers, compensation figures) before rendering.",
        styles['callout']
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


# ==============================================================================
# 4. CLOUD OPERATIONS RUNBOOK: Incident Management & Cloud Run Deployments
# ==============================================================================
CLOUD_OPS_RUNBOOK_MD = """# Cloud DevOps Runbook: Production Incident Management & Deployment Standard
**Document ID**: OPS-RUNBOOK-2026-v1  
**Applicability**: SRE, Cloud Infrastructure, and Core Engineering  
**Platform**: Google Cloud Platform (Cloud Run, Vertex AI, Firestore)  
**Owner**: Site Reliability Engineering (SRE)  

---

## 1. Production Architecture Overview
cortex.ai runs as serverless container workloads on **Google Cloud Run (us-central1)** with auto-scaling to zero (`min-instances 0`, `max-instances 2`). Data persistence utilizes **Cloud Firestore Native**, and machine learning routing is executed via **Vertex AI Gemini 2.5 Flash**.

---

## 2. Standard Deployment Schedule & Freeze Windows
* **Normal Release Window**: Tuesday and Thursday between 10:00 AM – 2:00 PM UTC.
* **Friday & Weekend Freeze**: No non-emergency production deployments are permitted between Friday 12:00 PM UTC and Monday 8:00 AM UTC.
* **Quarterly Peak Freeze**: Final 5 business days of each fiscal quarter.

---

## 3. High-Risk Infrastructure Mutations & Human-in-the-Loop Sign-off
Certain operational actions can disrupt live traffic and are strictly classified as **High-Risk Mutations**:
1. Restarting Cloud Run microservices (`hr-api`, `payroll-api`, `cortex-hub`).
2. Dropping or migrating Cloud Firestore database collections.
3. Modifying VPC firewall rules or IAM Service Account permissions.

**Governance Rule**: The `ops_agent` in cortex.ai is strictly prohibited from executing automated restarts or scale modifications without an explicit **Human-in-the-Loop Approval Confirmation Card** signed off by an authorized DevOps Engineer (`bob_ops`).

---

## 4. Emergency Rollback Standard Operating Procedure (SOP)
In the event of elevated 5xx error rates (>1.0% over 5 minutes) following a release:
1. **Traffic Reversion**:
   ```bash
   gcloud run services update-traffic cortex-hub --to-revisions=PREVIOUS_REVISION=100 --region=us-central1
   ```
2. **Verify Pod & Container Status**: Inspect Cloud Logging error traces for uncaught exceptions.
3. **Notify Command Center**: Post incident notice in `#incident-sre` Slack/Teams channel with rollback timestamp.
"""

def build_cloud_ops_pdf():
    pdf_path = BASE_DIR / "Cloud_Operations_and_Deployment_Runbook.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = get_pdf_styles()
    story = []

    story.append(Paragraph("Cloud DevOps Runbook: Incident Management", styles['title']))
    story.append(Paragraph("Document ID: OPS-RUNBOOK-2026-v1 | Google Cloud Run, Vertex AI & Firestore | SRE Team", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=12))

    story.append(Paragraph("1. Production Architecture & Sizing", styles['h1']))
    story.append(Paragraph(
        "cortex.ai workloads run containerized on Google Cloud Run with serverless scale-to-zero economics. Production guardrails restrict maximum concurrent instances to 2, ensuring budget protection within the $300 GCP credit allocation.",
        styles['body']
    ))

    story.append(Paragraph("2. Change Windows & Release Freezes", styles['h1']))
    story.append(Paragraph("• <b>Standard Release Windows:</b> Tuesdays & Thursdays (10:00 AM – 2:00 PM UTC).", styles['bullet']))
    story.append(Paragraph("• <b>Weekend Freeze:</b> Production deployments are frozen from Friday 12:00 PM UTC through Monday 8:00 AM UTC.", styles['bullet']))
    story.append(Paragraph("• <b>Quarter-End Freeze:</b> No releases during the final 5 business days of each fiscal quarter.", styles['bullet']))

    story.append(Paragraph("3. High-Risk Mutations & Human-in-the-Loop Safeguards", styles['h1']))
    story.append(Paragraph(
        "Infrastructure restarts, database migrations, and IAM modifications cannot be performed autonomously. cortex.ai automatically generates an amber <b>Pending Confirmation Action Card</b> that holds the execution until human DevOps sign-off is confirmed.",
        styles['body']
    ))

    story.append(Paragraph("4. Emergency Cloud Run Traffic Rollback", styles['h1']))
    story.append(Paragraph(
        "If 5xx errors exceed 1.0%, revert traffic immediately using: <br/><code>gcloud run services update-traffic cortex-hub --to-revisions=PREVIOUS=100</code>",
        styles['callout']
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


# ==============================================================================
# 5. SAMPLE RECEIPT / INVOICE FOR DOCUMENT AI OCR TESTING
# ==============================================================================
def build_sample_receipt_pdf():
    pdf_path = BASE_DIR / "Sample_Expense_Receipt_CloudConf2026.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=72,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    styles = get_pdf_styles()
    story = []

    story.append(Paragraph("ITEMIZED EXPENSE RECEIPT", styles['title']))
    story.append(Paragraph("Merchant: The Grand Bay Hotel & Conference Center | Singapore", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#718096"), spaceAfter=15))

    receipt_meta = [
        ["Receipt Number:", "INV-2026-98421", "Transaction Date:", "October 14, 2026"],
        ["Guest / Employee:", "Sarah Connor (Finance)", "Payment Method:", "Corporate Visa (*4492)"],
        ["Event / Purpose:", "Google Cloud JAPAC Summit", "Currency:", "USD ($)"]
    ]
    t_meta = Table(receipt_meta, colWidths=[1.8*inch, 2.0*inch, 1.8*inch, 1.4*inch])
    t_meta.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#2D3748")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    # Itemized lines
    items_data = [
        ["Item Description", "Qty", "Unit Price", "Total Amount"],
        ["Conference Delegate Accommodation (Night 1)", "1", "$180.00", "$180.00"],
        ["Conference Delegate Accommodation (Night 2)", "1", "$180.00", "$180.00"],
        ["Business Networking Dinner (Per Diem Policy Compliant)", "1", "$32.50", "$32.50"],
        ["High-Speed In-Room Workstation Wi-Fi", "2", "$12.00", "$24.00"],
        ["Subtotal", "", "", "$416.50"],
        ["Service Charge (10%)", "", "", "$41.65"],
        ["Local Goods & Services Tax (GST 9%)", "", "", "$37.49"],
        ["TOTAL PAID (USD)", "", "", "$495.64"]
    ]
    t_items = Table(items_data, colWidths=[3.6*inch, 0.8*inch, 1.2*inch, 1.4*inch])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('GRID', (0,0), (-1,-5), 0.5, colors.HexColor("#E2E8F0")),
        ('FONTNAME', (0,1), (-1,-5), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-5), 8.5),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('BACKGROUND', (0,-4), (-1,-1), colors.HexColor("#F7FAFC")),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,-1), (-1,-1), 10),
        ('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor("#2B6CB0")),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor("#2B6CB0")),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Document AI Verification Stamp:</b>", styles['body']))
    story.append(Paragraph(
        "Status: VERIFIED & PARSED BY GOOGLE CLOUD DOCUMENT AI EXPENSE PROCESSOR<br/>"
        "Extracted Entities: Total=$495.64 | Currency=USD | Vendor='The Grand Bay Hotel' | Date=2026-10-14",
        styles['callout']
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


def build_sample_invoice_pdf():
    pdf_path = BASE_DIR / "Sample_Vendor_Invoice_CloudServices.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=72,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    styles = get_pdf_styles()
    story = []

    story.append(Paragraph("TAX INVOICE / BILL OF SUPPLY", styles['title']))
    story.append(Paragraph("Vendor: CloudScale Systems & Solutions Ltd. | Enterprise Partner", styles['subtitle']))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#718096"), spaceAfter=15))

    inv_meta = [
        ["Invoice Number:", "INV-2026-CS-7819", "Invoice Date:", "October 10, 2026"],
        ["Billed To:", "cortex.ai Operations Dept.", "Payment Terms:", "Net 30 Days"],
        ["Purchase Order:", "PO-99412-DEV", "Due Date:", "November 9, 2026"]
    ]
    t_meta = Table(inv_meta, colWidths=[1.8*inch, 2.0*inch, 1.8*inch, 1.4*inch])
    t_meta.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#2D3748")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    items_data = [
        ["Line Item / Service Description", "Qty", "Rate (USD)", "Amount (USD)"],
        ["Enterprise API Gateway Provisioning (Dedicated Pods)", "1 Month", "$150.00", "$150.00"],
        ["Cloud Storage Multi-Regional Replication Tier", "500 GB", "$0.08", "$40.00"],
        ["Document AI OCR Processing Quota (5,000 pages)", "1 Package", "$45.00", "$45.00"],
        ["Subtotal", "", "", "$235.00"],
        ["Sales Tax / VAT (8%)", "", "", "$18.80"],
        ["TOTAL INVOICE AMOUNT (USD)", "", "", "$253.80"]
    ]
    t_items = Table(items_data, colWidths=[3.6*inch, 0.8*inch, 1.2*inch, 1.4*inch])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('GRID', (0,0), (-1,-4), 0.5, colors.HexColor("#E2E8F0")),
        ('FONTNAME', (0,1), (-1,-4), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-4), 8.5),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('BACKGROUND', (0,-3), (-1,-1), colors.HexColor("#F7FAFC")),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,-1), (-1,-1), 10),
        ('TEXTCOLOR', (0,-1), (-1,-1), colors.HexColor("#2B6CB0")),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor("#2B6CB0")),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Document AI Extracted Metadata:</b>", styles['body']))
    story.append(Paragraph(
        "Invoice Total: $253.80 | Supplier: CloudScale Systems & Solutions Ltd. | Invoice ID: INV-2026-CS-7819 | Line Items: 3",
        styles['callout']
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {pdf_path}")


def main():
    print(f"Creating sample enterprise knowledge base in: {BASE_DIR}")
    
    # 1. Write Markdown files
    (BASE_DIR / "HR_Employee_Handbook_and_Leave_Policy.md").write_text(HR_POLICY_MD, encoding="utf-8")
    (BASE_DIR / "Finance_and_Travel_Expense_Policy.md").write_text(FINANCE_POLICY_MD, encoding="utf-8")
    (BASE_DIR / "IT_Security_and_Data_Protection_Policy.md").write_text(IT_SECURITY_POLICY_MD, encoding="utf-8")
    (BASE_DIR / "Cloud_Operations_and_Deployment_Runbook.md").write_text(CLOUD_OPS_RUNBOOK_MD, encoding="utf-8")
    print("✓ Created 4 Markdown policy documents.")

    # 2. Build PDF files using ReportLab
    build_hr_pdf()
    build_finance_pdf()
    build_it_security_pdf()
    build_cloud_ops_pdf()
    build_sample_receipt_pdf()
    build_sample_invoice_pdf()
    print("✓ Created 6 PDF documents (including sample Document AI invoice and receipt).")
    print(f"\nAll files successfully stored in: {BASE_DIR}")

if __name__ == "__main__":
    main()
