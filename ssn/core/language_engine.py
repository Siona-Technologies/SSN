"""
SSN Language Engine (Phase 1)

Simple simulated LLM brain for:
- OWNER (rich output, uses context)
- GUEST (restricted)
"""

from __future__ import annotations
from typing import Any, Dict, Optional


class LanguageEngine:
    """
    Dummy LLM module (Phase 1)
    """

    def __init__(self):
        self.engine_name = "ssn-language-dummy-v1"

    def process(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        role: str = "GUEST"
    ) -> Dict[str, Any]:
        """
        Universal method expected by BrainRouter.
        Returns a structured response.
        """

        if role == "OWNER":
            return {
                "reply": (
                    f"[SSN → Samson]: I received your request and processed it "
                    f"using the Phase 1 language core.\n\n"
                    f"Your message was: \"{text}\"\n\n"
                    f"[Context used: {bool(context)}]"
                ),
                "role": "OWNER",
                "used_context": bool(context),
                "engine": self.engine_name
            }

        else:
            return {
                "reply": f"[SSN → Guest]: I received your message: \"{text}\".",
                "role": "GUEST",
                "used_context": False,
                "engine": self.engine_name
            }
