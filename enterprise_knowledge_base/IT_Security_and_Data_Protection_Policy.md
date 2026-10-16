# Enterprise Cybersecurity, Data Classification & Identity Governance Policy
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
