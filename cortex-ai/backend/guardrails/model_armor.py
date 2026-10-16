"""
cortex.ai - Model Armor & Gemma Safety Guardrails
Provides real-time safety screening against prompt injection attacks, jailbreaks,
and prevents PII / sensitive bank leakage using Google ShieldGemma & Model Armor.
"""

import os
import re
from typing import Dict, Any, Tuple
from pydantic import BaseModel

try:
    from .gemma_guardrail import gemma_guardrail, GemmaGuardrailResult
except ImportError:
    from guardrails.gemma_guardrail import gemma_guardrail, GemmaGuardrailResult

class GuardrailResult(BaseModel):
    is_safe: bool
    flagged: bool
    threat_category: str = "NONE" # PROMPT_INJECTION, PII_LEAKAGE, JAILBREAK, SYSTEM_EXTRACTION
    details: str = "Clear"
    cleaned_text: str = ""
    guardrail_model: str = "google/shieldgemma-2b"

class ModelArmor:
    def __init__(self):
        self.enabled = os.getenv("MODEL_ARMOR_ENABLED", "true").lower() in ("true", "1", "yes")
        self.gemma = gemma_guardrail

    def screen_prompt(self, prompt: str) -> GuardrailResult:
        if not self.enabled:
            return GuardrailResult(
                is_safe=True,
                flagged=False,
                details="Model Armor Disabled",
                cleaned_text=prompt,
                guardrail_model="disabled"
            )

        # Execute ShieldGemma Safety Evaluation
        gemma_res = self.gemma.screen_prompt(prompt)
        if not gemma_res.is_safe:
            return GuardrailResult(
                is_safe=False,
                flagged=True,
                threat_category=gemma_res.threat_category,
                details=f"Model Armor & ShieldGemma Alert: Adversarial threat detected in category '{gemma_res.threat_category}'. {gemma_res.details}",
                cleaned_text="",
                guardrail_model=gemma_res.guardrail_model
            )

        return GuardrailResult(
            is_safe=True,
            flagged=False,
            threat_category="NONE",
            details="Prompt passed Model Armor & Google ShieldGemma safety filters",
            cleaned_text=prompt,
            guardrail_model=gemma_res.guardrail_model
        )

    def screen_response(self, text: str) -> str:
        if not self.enabled:
            return text
        return self.gemma.screen_response(text)

model_armor = ModelArmor()

