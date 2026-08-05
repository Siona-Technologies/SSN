"""
Documentation consistency for Phase 2 closeout / Vision Charter.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CORE_DOCS = [
    ROOT / "docs" / "SIONA_VISION_CHARTER.md",
    ROOT / "docs" / "PHASE_2_ACCEPTANCE.md",
    ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md",
    ROOT / "docs" / "PHASE_STATUS.md",
    ROOT / "docs" / "SIONA_VISION.md",
    ROOT / "docs" / "SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md",
    ROOT / "docs" / "SIONA_PHASE_ROADMAP.md",
    ROOT / "docs" / "adr" / "0001-hybrid-runtime-integration.md",
    ROOT / "docs" / "DEFERRED_CAPABILITIES.md",
    ROOT / "docs" / "HARDWARE_ROADMAP.md",
    ROOT / "docs" / "TECHNICAL_DEBT_REGISTER.md",
    ROOT / "docs" / "EXPERIMENT_LOG.md",
    ROOT / "docs" / "PHASE_3B_HARDWARE_INVENTORY.md",
    ROOT / "docs" / "PHASE_3B_MODEL_INDEPENDENCE.md",
    ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md",
    ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md",
    ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md",
    ROOT / "docs" / "SIONA_BUILD_PLAN.md",
    ROOT / "docs" / "SIONA_AWS_ARCHITECTURE_SHOWCASE.md",
]

BANNED_PRODUCT = re.compile(r"\b(Pulse|Weza AI|Weza|Jarvis)\b", re.IGNORECASE)
BANNED_CLAIM = re.compile(
    r"trained SIONA-native foundation model exists|"
    r"deterministic neuromorphic provider is a trained SNN|"
    r"models? (?:may|can|should) directly command unrestricted",
    re.IGNORECASE,
)


class TestPhase2CloseoutDocs(unittest.TestCase):
    def test_required_closeout_docs_exist(self):
        for path in (
            ROOT / "docs" / "SIONA_VISION_CHARTER.md",
            ROOT / "docs" / "PHASE_2_ACCEPTANCE.md",
            ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md",
        ):
            self.assertTrue(path.is_file(), f"missing {path}")

    def test_vision_charter_core_principles(self):
        text = (ROOT / "docs" / "SIONA_VISION_CHARTER.md").read_text(encoding="utf-8")
        plain = re.sub(r"\*+", "", text).lower()
        self.assertIn("One brain, many bodies", text)
        self.assertIn("SIBONA", text)
        self.assertIn("not implemented in phase 2", plain)
        self.assertIn("never directly command unrestricted physical actuators", plain)
        self.assertIn("Trace IDs are not authentication", text)

    def test_phase_status_labels(self):
        text = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("7b92114", text)
        self.assertIn("19b3b13", text)
        self.assertNotIn("Final branch tip", text)
        self.assertIn("d6c17d0", text)
        self.assertIn("2e6abb6", text)
        self.assertIn("Completed and hosted-CI accepted", text)
        self.assertIn("Phase 3A completed; Phase 3B research recorded", text)
        self.assertIn(
            "first runtime/model baseline installed and artifact-verified locally; limited loopback inference completed; provider integration and full evaluation pending",
            text,
        )
        self.assertIn("provider integration", text.lower())
        self.assertIn("unverified", text.lower())
        self.assertIn("SIONA_VISION_CHARTER.md", text)
        self.assertIn("PHASE_2_ACCEPTANCE.md", text)
        self.assertIn("PHASE_3_ENGINEERING_SPEC.md", text)
        self.assertIn("not started", text.lower())  # Phase 4 remains not started
        self.assertIn("PHASE_3B_HARDWARE_INVENTORY.md", text)
        self.assertIn("0003-first-local-model-strategy.md", text)
        self.assertNotIn("Phase 3A status (this branch)", text)
        self.assertNotIn("not marked accepted until", text)

    def test_phase3_spec_status(self):
        # Phase 3A completed/merged; Phase 3 overall in progress; Phase 3B research recorded.
        text = (ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md").read_text(encoding="utf-8")
        self.assertIn("phase 3a", text.lower())
        self.assertIn("completed", text.lower())
        self.assertIn("in progress", text.lower())
        self.assertIn("phase 3b", text.lower())
        self.assertIn("d6c17d0", text)
        self.assertIn("2e6abb6", text)
        self.assertIn("install or download a real model", text.lower())

    def test_phase3b_planning_docs_exist(self):
        for path in (
            ROOT / "docs" / "PHASE_3B_HARDWARE_INVENTORY.md",
            ROOT / "docs" / "PHASE_3B_MODEL_INDEPENDENCE.md",
            ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md",
            ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md",
            ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md",
        ):
            self.assertTrue(path.is_file(), f"missing {path}")
        independence = (ROOT / "docs" / "PHASE_3B_MODEL_INDEPENDENCE.md").read_text(
            encoding="utf-8"
        )
        plain = re.sub(r"\*+", "", independence).lower()
        self.assertIn("does not currently own a trained foundation model", plain)
        self.assertIn("replaceable", plain)
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Proposed", adr)
        self.assertIn("No final runtime or model is approved", adr)

    def test_phase3b_official_research_gate(self):
        research = (ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md").read_text(
            encoding="utf-8"
        )
        # Research must contain completed comparisons, not only unresolved placeholders.
        self.assertIn("Provisional runtime recommendation", research)
        self.assertIn("PROVISIONAL — REQUIRES OWNER APPROVAL BEFORE INSTALLATION", research)
        self.assertIn("PROVISIONAL — NO MODEL DOWNLOAD AUTHORIZED", research)
        self.assertIn("llama.cpp native Windows", research)
        self.assertIn("Qwen3-1.7B", research)
        self.assertNotIn(
            "Do not fill unstable facts from memory",
            research,
        )
        # Ensure the document is not still the empty template form.
        self.assertGreater(research.count("Officially stated"), 10)
        # Full comparison coverage and traceability.
        for heading in (
            "### 1. llama.cpp native Windows CPU",
            "### 2. llama.cpp Windows SYCL",
            "### 3. llama.cpp Windows Vulkan",
            "### 4. Ollama for Windows",
            "### 5. LM Studio",
            "### 6. OpenVINO GenAI",
            "### 7. ONNX Runtime GenAI / WinML / DirectML",
            "### Candidate A — Qwen3-1.7B",
            "### Candidate B — Qwen3-4B",
            "### Candidate C — IBM Granite 4.0 Micro",
            "### Candidate D — Microsoft Phi-4-mini-instruct",
            "### Candidate E — Qwen3.5-2B",
        ):
            self.assertIn(heading, research)
        self.assertIn("## Source traceability appendix", research)
        self.assertIn("Exact release, version, tag or revision examined", research)
        self.assertIn("Original repository revision", research)
        self.assertIn("Quantized repository revision", research)
        self.assertIn("In progress", research)
        self.assertIn("Phase 4", research)
        self.assertIn("**Not started**", research)
        runbook = (ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("UNAPPROVED", runbook)
        self.assertIn("18211732", runbook)
        self.assertIn(
            "f98e6690faad6a8718451d420a63cbfde6c87028beae4e7f35a36a762730cefd",
            runbook,
        )
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertIn("provider integration", status.lower())
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Proposed", status_block)
        self.assertNotIn("Accepted", status_block)
        self.assertIn("PROVISIONAL — NO MODEL DOWNLOAD AUTHORIZED", research)
        self.assertIn("installation", research.lower())
        self.assertIn("provider integration", research.lower())

    def test_phase3b_owner_approved_baseline(self):
        research = (ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md").read_text(
            encoding="utf-8"
        )
        runbook = (ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md").read_text(
            encoding="utf-8"
        )
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        experiment = (ROOT / "docs" / "EXPERIMENT_LOG.md").read_text(encoding="utf-8")
        combined = "\n".join([research, runbook, status, adr, experiment])
        self.assertIn("llama.cpp", combined)
        self.assertIn("b9968", combined)
        self.assertIn("1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f", combined)
        self.assertIn("Qwen3-1.7B-Q4_K_M.gguf", combined)
        self.assertIn("ggml-org", combined)
        self.assertIn("daeb8e2d528a760970442092f6bf1e55c3b659eb", combined)
        self.assertIn(
            "d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5",
            combined,
        )
        self.assertIn("pre-installation verification", combined.lower())
        self.assertIn("OWNER-APPROVED FOR PRE-INSTALLATION VERIFICATION ONLY", research)
        self.assertIn("provider integration", runbook.lower())
        self.assertIn("unverified", status.lower())
        self.assertIn("In progress", status)
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Proposed", status_block)
        self.assertNotIn("Accepted", status_block)
        self.assertIn("## Owner-approved Phase 3B baseline", adr)
        self.assertIn("EXP-3B-002", experiment)
        self.assertIn("quantizer", runbook.lower())
        # Quantizer must be identified as ggml-org for the approved Q4_K_M path.
        self.assertIn("Quantizer | ggml-org", runbook.replace("`", ""))

    def test_phase3b_install_execution_evidence(self):
        research = (ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md").read_text(
            encoding="utf-8"
        )
        runbook = (ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md").read_text(
            encoding="utf-8"
        )
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        experiment = (ROOT / "docs" / "EXPERIMENT_LOG.md").read_text(encoding="utf-8")
        combined = "\n".join([research, runbook, status, adr, experiment])
        self.assertIn("18211732", combined)
        self.assertIn(
            "f98e6690faad6a8718451d420a63cbfde6c87028beae4e7f35a36a762730cefd",
            combined,
        )
        self.assertIn("1282439264", combined)
        self.assertIn(
            "d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5",
            combined,
        )
        self.assertIn(
            "INSTALLED AND ARTIFACT-VERIFIED LOCALLY; LIMITED LOOPBACK EXECUTION COMPLETED",
            research,
        )
        self.assertIn("Local loopback inference is working.", experiment)
        self.assertIn(
            "LOCAL SHORT-PROBE OBSERVATION — NOT A PRODUCTION PERFORMANCE CLAIM",
            experiment,
        )
        self.assertIn("runtime currently **stopped**", status.lower())
        self.assertIn("not listening", status.lower())
        self.assertIn("application-level graceful shutdown", experiment.lower())
        self.assertIn("not verified", experiment.lower())
        self.assertIn("Stop-Process without -Force", experiment)
        self.assertIn("provider integration", combined.lower())
        self.assertIn("EXP-3B-003", experiment)
        self.assertIn("unverified** beyond basic", status.lower())
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Proposed", status_block)
        self.assertNotIn("Accepted", status_block)
        self.assertIn("In progress", status)
        self.assertIn("Phase 4 remains **not started**", status)
        # No binary artifacts should be referenced as committed repo paths.
        self.assertNotIn("```gguf", combined.lower())

    def test_no_banned_product_names_in_core_docs(self):
        for path in CORE_DOCS:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(BANNED_PRODUCT.search(text), f"banned product name in {path}")

    def test_no_false_capability_claims_in_core_docs(self):
        for path in CORE_DOCS:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(BANNED_CLAIM.search(text), f"false capability claim in {path}")

    def test_sibona_only_as_working_name(self):
        charter = (ROOT / "docs" / "SIONA_VISION_CHARTER.md").read_text(encoding="utf-8")
        plain = re.sub(r"\*+", "", charter).lower()
        self.assertIn("working name", plain)
        self.assertIn("not a separate intelligence core", plain)


if __name__ == "__main__":
    unittest.main()
