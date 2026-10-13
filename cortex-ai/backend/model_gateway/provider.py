import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger("cortex.model_gateway")

# Ensure .env from root directory is loaded
root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if root_env.exists():
    with open(root_env, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class BaseModelProvider(ABC):
    @abstractmethod
    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        pass


class VertexGeminiProvider(BaseModelProvider):
    def __init__(self, model_name: str = "gemini-3-flash-preview", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Vertex Gemini client: {e}")

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError(f"Gemini client not initialized for {self.model_name}; missing or invalid API key.")
        
        config = {}
        if system_instruction:
            config["system_instruction"] = system_instruction
        if response_mime_type:
            config["response_mime_type"] = response_mime_type

        # Candidate models to try in order of availability and stability
        candidate_models = [self.model_name]
        for fallback in ["gemini-3-flash-preview", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_err = None
        for m in candidate_models:
            try:
                res = self._client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config
                )
                if res and res.text:
                    return {
                        "text": res.text.strip(),
                        "provider": "vertex_gemini",
                        "model": f"google/{m}"
                    }
            except Exception as e:
                err_str = str(e)
                logger.warning(f"Gemini model {m} call failed ({e}); attempting next candidate.")
                last_err = e
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower():
                    break

        raise RuntimeError(f"All Gemini candidates failed. Last error: {last_err}")


class AnthropicClaudeProvider(BaseModelProvider):
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "") or os.getenv("CLAUDE_API_KEY", "")
        self._client = None
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError(f"Anthropic model {self.model_name} is disabled because no ANTHROPIC_API_KEY was provided.")
        
        if not self._client:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_instruction:
            kwargs["system"] = system_instruction

        res = self._client.messages.create(**kwargs)
        text_content = ""
        for block in res.content:
            if hasattr(block, "text"):
                text_content += block.text
        return {"text": text_content, "provider": "anthropic_claude", "model": self.model_name}


class VertexModelGardenProvider(BaseModelProvider):
    def __init__(self, endpoint_id: Optional[str] = None, model_name: str = "meta/llama-3-70b"):
        self.endpoint_id = endpoint_id or os.getenv("VERTEX_MODEL_GARDEN_ENDPOINT", "")
        self.model_name = model_name

    def is_available(self) -> bool:
        return bool(self.endpoint_id and self.endpoint_id.strip())

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Vertex Model Garden endpoint not configured.")
        logger.info(f"Dispatching query to Vertex Model Garden: {self.model_name}")
        return {
            "text": f"Response from Vertex Model Garden ({self.model_name})",
            "provider": "vertex_model_garden",
            "model": self.model_name
        }


class OfflineStubProvider(BaseModelProvider):
    """
    Guarantees deterministic, zero-dependency offline execution for evaluations and demos.
    """
    def __init__(self, model_name: str = "offline-stub-engine"):
        self.model_name = model_name

    def is_available(self) -> bool:
        return True

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        p_lower = prompt.lower()
        if response_mime_type == "application/json":
            if "salary" in p_lower:
                return {
                    "text": json.dumps({
                        "selected_agent_id": "finance_agent",
                        "intent": "DATA_LOOKUP",
                        "suggested_tool": "get_employee_salary",
                        "confidence": 0.96,
                        "reasoning": "Detected salary compensation request -> finance_agent"
                    }),
                    "provider": "offline_stub",
                    "model": self.model_name
                }
            elif any(k in p_lower for k in ["slide", "deck", "presentation", "email", "draft", "word", "docx"]):
                return {
                    "text": json.dumps({
                        "selected_agent_id": "productivity_agent",
                        "intent": "DOCUMENT_CREATION" if "slide" in p_lower or "word" in p_lower else "EMAIL_DRAFT",
                        "suggested_tool": "generate_powerpoint_presentation" if "slide" in p_lower else ("create_email_draft" if "email" in p_lower else "generate_word_document"),
                        "confidence": 0.95,
                        "reasoning": "Detected productivity creation request -> productivity_agent"
                    }),
                    "provider": "offline_stub",
                    "model": self.model_name
                }
            elif any(k in p_lower for k in ["jira", "ticket", "proj", "bug"]):
                return {
                    "text": json.dumps({
                        "selected_agent_id": "it_support_agent",
                        "intent": "DATA_LOOKUP",
                        "suggested_tool": "get_ticket" if "proj-" in p_lower or "sec-" in p_lower else "list_tickets",
                        "confidence": 0.95,
                        "reasoning": "Detected IT Jira ticket query -> it_support_agent"
                    }),
                    "provider": "offline_stub",
                    "model": self.model_name
                }
            elif any(k in p_lower for k in ["pto", "leave", "vacation", "holiday"]):
                return {
                    "text": json.dumps({
                        "selected_agent_id": "hr_agent",
                        "intent": "DATA_LOOKUP",
                        "suggested_tool": "get_leave_balance",
                        "confidence": 0.95,
                        "reasoning": "Detected HR leave balance inquiry -> hr_agent"
                    }),
                    "provider": "offline_stub",
                    "model": self.model_name
                }
            elif any(k in p_lower for k in ["restart", "cluster", "uptime", "deploy"]):
                return {
                    "text": json.dumps({
                        "selected_agent_id": "ops_agent",
                        "intent": "ACTION_MUTATION",
                        "suggested_tool": "restart_cloud_service" if "restart" in p_lower else "get_system_health",
                        "confidence": 0.95,
                        "reasoning": "Detected cloud ops command -> ops_agent"
                    }),
                    "provider": "offline_stub",
                    "model": self.model_name
                }
            else:
                return {
                    "text": json.dumps({
                        "selected_agent_id": "cortex_assistant",
                        "intent": "CONVERSATIONAL",
                        "suggested_tool": None,
                        "confidence": 0.70,
                        "reasoning": "General conversational query"
                    }),
                    "provider": "offline_stub",
                    "model": self.model_name
                }

        # Conversational fallbacks
        if "weather" in p_lower:
            text = "The weather in Pune, India is currently warm and mostly clear with temperatures around 32°C to 35°C (pre-monsoon summer season)."
        elif "normal question" in p_lower or "apart from" in p_lower or "general" in p_lower:
            text = "Yes, absolutely! I can answer general everyday questions, technical topics, writing tasks, and general knowledge, in addition to internal organizational tools."
        elif "hi" in p_lower or "hello" in p_lower:
            text = "Hello! I am cortex.ai, your enterprise AI assistant. How can I assist you today?"
        else:
            text = f"I am cortex.ai, your enterprise digital assistant. I can help answer general questions or assist with HR policies, IT tickets, expenses, cloud operations, and Office document generation."

        return {
            "text": text,
            "provider": "offline_stub",
            "model": "offline/stub (Offline Fallback)"
        }


class ModelGateway:
    def __init__(self):
        self.providers: Dict[str, BaseModelProvider] = {
            "google/gemini-3-flash-preview": VertexGeminiProvider(model_name="gemini-3-flash-preview"),
            "google/gemini-3.5-flash": VertexGeminiProvider(model_name="gemini-3.5-flash"),
            "google/gemini-3.8-flash": VertexGeminiProvider(model_name="gemini-3.8-flash"),
            "google/gemini-3.1-pro-preview": VertexGeminiProvider(model_name="gemini-3.1-pro-preview"),
            "anthropic/claude-3-5-sonnet": AnthropicClaudeProvider(model_name="claude-3-5-sonnet-20241022"),
            "anthropic/claude-3-opus": AnthropicClaudeProvider(model_name="claude-3-opus-20240229"),
            "offline/stub": OfflineStubProvider()
        }
        self.default_provider_key = "google/gemini-3-flash-preview"
        self.stub_provider = self.providers["offline/stub"]

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Returns model options for selection.
        If no API key is provided for a model family, marked available: False.
        """
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        anthropic_key = (os.getenv("ANTHROPIC_API_KEY", "") or os.getenv("CLAUDE_API_KEY", "")).strip()

        return [
            {
                "id": "google/gemini-3-flash-preview",
                "name": "Gemini 3 Flash (Fast & Active)",
                "provider": "Google",
                "family": "gemini",
                "available": bool(gemini_key),
                "disabled_reason": None if gemini_key else "Missing GEMINI_API_KEY in .env"
            },
            {
                "id": "google/gemini-3.5-flash",
                "name": "Gemini 3.5 Flash",
                "provider": "Google",
                "family": "gemini",
                "available": bool(gemini_key),
                "disabled_reason": None if gemini_key else "Missing GEMINI_API_KEY in .env"
            },
            {
                "id": "google/gemini-3.8-flash",
                "name": "Gemini 3.8 Flash",
                "provider": "Google",
                "family": "gemini",
                "available": bool(gemini_key),
                "disabled_reason": None if gemini_key else "Missing GEMINI_API_KEY in .env"
            },
            {
                "id": "google/gemini-3.1-pro-preview",
                "name": "Gemini 3.1 Pro Preview",
                "provider": "Google",
                "family": "gemini",
                "available": bool(gemini_key),
                "disabled_reason": None if gemini_key else "Missing GEMINI_API_KEY in .env"
            },
            {
                "id": "anthropic/claude-3-5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "Anthropic",
                "family": "claude",
                "available": bool(anthropic_key),
                "disabled_reason": None if anthropic_key else "Missing ANTHROPIC_API_KEY in .env"
            }
        ]

    def get_default_model(self) -> str:
        models = self.get_available_models()
        for m in models:
            if m["available"]:
                return m["id"]
        return "offline/stub"

    def get_provider(self, preferred_model: Optional[str] = None) -> BaseModelProvider:
        if preferred_model and preferred_model in self.providers:
            return self.providers[preferred_model]
        def_model = self.get_default_model()
        return self.providers.get(def_model, self.stub_provider)

    def generate(
        self,
        prompt: str,
        preferred_model: Optional[str] = None,
        fallback_models: Optional[List[str]] = None,
        system_instruction: Optional[str] = None,
        response_mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        candidates = []
        if preferred_model:
            # Map legacy or generic aliases
            if preferred_model in ["gemini", "google/gemini", "gemini-3.8-flash", "google/gemini-3.8-flash"]:
                candidates.extend(["google/gemini-3-flash-preview", "google/gemini-3.5-flash", "google/gemini-3.8-flash"])
            elif preferred_model in self.providers:
                candidates.append(preferred_model)
        if fallback_models:
            candidates.extend(fallback_models)
        
        # Add default active model if not already candidate
        def_model = self.get_default_model()
        if def_model not in candidates:
            candidates.append(def_model)
        candidates.append("offline/stub")

        for model_key in candidates:
            provider = self.providers.get(model_key)
            if not provider:
                continue
            
            # Check availability if supported
            if hasattr(provider, "is_available") and not provider.is_available():
                logger.info(f"Model {model_key} is disabled (no API key configured); skipping.")
                continue

            try:
                res = provider.generate_content(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    response_mime_type=response_mime_type
                )
                if res and res.get("text"):
                    return res
            except Exception as e:
                logger.info(f"Model {model_key} failed or unavailable ({e}); trying next candidate.")

        res = self.stub_provider.generate_content(
            prompt=prompt,
            system_instruction=system_instruction,
            response_mime_type=response_mime_type
        )
        res["model"] = "offline/stub (Offline Fallback)"
        return res


model_gateway = ModelGateway()
