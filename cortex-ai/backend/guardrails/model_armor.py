"""
cortex.ai - Model Armor Guardrails
Provides real-time safety screening against prompt injection attacks and prevents PII / sensitive bank leakage.
"""

import os
import re
from typing import Dict, Any, Tuple
from pydantic import BaseModel

class GuardrailResult(BaseModel):
    is_safe: bool
    flagged: bool
    threat_category: str = "NONE" # PROMPT_INJECTION, PII_LEAKAGE, JAILBREAK
    details: str = "Clear"
    cleaned_text: str = ""

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"override (system|security) (rules|prompt)",
    r"you are now in (dan|jailbreak|developer|god) mode",
    r"reveal (your )?(system|internal) (prompt|instructions)",
    r"bypass (authentication|policy|authorization)",
    r"disregard (all )?guidelines"
]

class ModelArmor:
    def __init__(self):
        self.enabled = os.getenv("MODEL_ARMOR_ENABLED", "true").lower() in ("true", "1", "yes")

    def screen_prompt(self, prompt: str) -> GuardrailResult:
        if not self.enabled:
            return GuardrailResult(is_safe=True, flagged=False, details="Model Armor Disabled", cleaned_text=prompt)

        p_lower = prompt.lower()
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, p_lower):
                return GuardrailResult(
                    is_safe=False,
                    flagged=True,
                    threat_category="PROMPT_INJECTION",
                    details=f"Model Armor Alert: Adversarial prompt injection detected matching pattern '{pattern}'.",
                    cleaned_text=""
                )

        return GuardrailResult(is_safe=True, flagged=False, details="Prompt passed Model Armor safety filters", cleaned_text=prompt)

    def screen_response(self, text: str) -> str:
        if not self.enabled:
            return text

        # Mask unmasked bank accounts (8-16 consecutive digits)
        masked_text = re.sub(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", "****-****-****-XXXX", text)
        masked_text = re.sub(r"\b\d{9,16}\b", "****MASKED****", masked_text)
        return masked_text

model_armor = ModelArmor()
