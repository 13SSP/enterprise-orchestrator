"""
cortex.ai - Productivity Agent
Integrates M365 (Outlook, Word, PowerPoint) and cross-domain data from other agents.
"""

from typing import Dict, Any, List

class ProductivityAgent:
    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest
        self.id = manifest["id"]
        self.name = manifest["name"]

    def process_query(self, query: str, context: Dict[str, Any], tools_available: List[str]) -> Dict[str, Any]:
        q_lower = query.lower()
        
        # 1. Slide Deck generation
        if "slide" in q_lower or "deck" in q_lower or "presentation" in q_lower or "powerpoint" in q_lower or "pptx" in q_lower:
            slides = [
                {
                    "title": "Executive Overview: Q4 Operations",
                    "bullets": ["Platform uptime at 99.99%", "All core services healthy and operational"],
                    "speaker_notes": "Emphasize stability across all cloud regions."
                },
                {
                    "title": "Open Engineering & IT Tickets",
                    "bullets": [
                        "PROJ-102: Latency spike in webhook processor (In Progress)",
                        "SEC-204: Port 22 remediation on staging compute (Critical, Open)",
                        "PROJ-101: Node pool cluster upgrade (In Progress)"
                    ],
                    "speaker_notes": "Review action items and target resolution timelines."
                },
                {
                    "title": "Next Steps & Roadmap",
                    "bullets": ["Deploy automated canary rollouts", "Complete SOC2 compliance checks"],
                    "speaker_notes": "Thank the team and open for questions."
                }
            ]
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "generate_powerpoint_presentation",
                "args": {
                    "deck_title": "Quarterly IT & Engineering Ticket Overview",
                    "deck_subtitle": "Prepared by cortex.ai Productivity Agent",
                    "slides": slides
                },
                "response_text": "I am generating a 3-slide PowerPoint presentation covering open IT tickets."
            }

        # 2. Word document generation
        elif "word" in q_lower or "docx" in q_lower or "memo" in q_lower or "report" in q_lower or "document" in q_lower:
            sections = [
                {
                    "heading": "1. Purpose & Scope",
                    "content": "This memorandum summarizes the current corporate policies and system status."
                },
                {
                    "heading": "2. Highlights & Observations",
                    "bullets": [
                        "Leave policy complies with 2026 workforce standards.",
                        "Zero critical security breaches recorded in the audit window."
                    ]
                }
            ]
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "generate_word_document",
                "args": {
                    "title": "Enterprise Operations Summary Memorandum",
                    "subtitle": "Confidential - For Internal Use Only",
                    "sections": sections
                },
                "response_text": "I am drafting and compiling your Word (.docx) document."
            }

        # 3. Email draft creation
        elif "email" in q_lower or "draft" in q_lower or "mail" in q_lower:
            user = context.get("user", {})
            user_name = user.get("name", "Employee")
            return {
                "agent_id": self.id,
                "action": "INVOKE_TOOL",
                "suggested_tool": "create_email_draft",
                "args": {
                    "recipient_email": "sarah.connor@company.internal",
                    "subject": "PTO Notification and Leave Balance Update",
                    "body": f"Hi Sarah,\n\nI checked my leave records and have remaining PTO available. I plan to take 3 days of leave next week.\n\nBest regards,\n{user_name}"
                },
                "response_text": "I have created an Outlook email draft for your manager. Please review and approve before sending."
            }

        return {
            "agent_id": self.id,
            "action": "CONVERSATIONAL",
            "response_text": f"Hello! I am the {self.name}. I can draft Outlook emails, create Word memos (.docx), and build slide decks (.pptx)."
        }

def create_agent(manifest: Dict[str, Any]) -> ProductivityAgent:
    return ProductivityAgent(manifest)
