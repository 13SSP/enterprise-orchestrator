# Cloud DevOps Runbook: Production Incident Management & Deployment Standard
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
