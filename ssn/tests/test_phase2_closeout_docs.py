"""Documentation consistency across Phase 2 and accepted Phase 3 closeout."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CORE_DOCS = [
    ROOT / "docs" / "SIONA_VISION_CHARTER.md",
    ROOT / "docs" / "PHASE_2_ACCEPTANCE.md",
    ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md",
    ROOT / "docs" / "PHASE_3B_ACCEPTANCE.md",
    ROOT / "docs" / "PHASE_STATUS.md",
    ROOT / "docs" / "SIONA_VISION.md",
    ROOT / "docs" / "SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md",
    ROOT / "docs" / "SIONA_PHASE_ROADMAP.md",
    ROOT / "docs" / "adr" / "0001-hybrid-runtime-integration.md",
    ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md",
    ROOT / "docs" / "DEFERRED_CAPABILITIES.md",
    ROOT / "docs" / "HARDWARE_ROADMAP.md",
    ROOT / "docs" / "TECHNICAL_DEBT_REGISTER.md",
    ROOT / "docs" / "EXPERIMENT_LOG.md",
    ROOT / "docs" / "PHASE_3B_HARDWARE_INVENTORY.md",
    ROOT / "docs" / "PHASE_3B_MODEL_INDEPENDENCE.md",
    ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md",
    ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md",
    ROOT / "docs" / "SIONA_BUILD_PLAN.md",
    ROOT / "docs" / "SIONA_AWS_ARCHITECTURE_SHOWCASE.md",
    ROOT / "docs" / "SIONA_IDENTITY_INFORMATION_GOVERNANCE.md",
    ROOT / "docs" / "SIONA_INFORMATION_CLASSIFICATION.md",
    ROOT / "docs" / "SIONA_CONSENT_AND_REVOCATION.md",
    ROOT / "docs" / "SIONA_PUBLIC_PROFILE_POLICY.md",
    ROOT / "docs" / "SIONA_PRIVATE_CONTEXT_POLICY.md",
    ROOT / "docs" / "SIONA_WEBSITE_CONTENT_AUDIT_PLAN.md",
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
            ROOT / "docs" / "PHASE_3B_ACCEPTANCE.md",
            ROOT / "docs" / "PHASE_STATUS.md",
            ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md",
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
        lower = text.lower()
        self.assertIn("7b92114", text)
        self.assertIn("19b3b13", text)
        self.assertIn("d6c17d0", text)
        self.assertIn("2e6abb6", text)
        self.assertIn("Completed and hosted-CI accepted", text)
        self.assertIn("Phase 3 | **Completed", text)
        self.assertIn("Phase 3B | **Completed and accepted", text)
        self.assertIn("ADR 0003 is **Accepted (Phase 3B)**", text)
        self.assertIn("State C", text)
        self.assertIn("EXP-3B-013", text)
        self.assertIn("Gate E", text)
        self.assertIn("EXP-3B-011", text)
        self.assertIn("EXP-3B-012", text)
        self.assertIn("chat=true", text)
        self.assertIn("NOT_VERIFIED", text)
        self.assertIn("UNSUPPORTED_ON_PINNED_BASELINE", text)
        self.assertIn("siona_native=false", text)
        self.assertIn("phase 4 remains **not started**", lower)
        self.assertNotIn("ADR 0003 acceptance and Phase 3B completion decision still pending", text)
        self.assertNotIn("Phase 3B remains **in progress**", text)
        self.assertNotIn("Phase 3B is **not** completed", text)
        self.assertNotIn("Phase 3A status (this branch)", text)
        self.assertNotIn("not marked accepted until", text)

    def test_phase3_spec_status(self):
        text = (ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md").read_text(encoding="utf-8")
        lower = text.lower()
        self.assertIn("phase 3 **completed**", lower)
        self.assertIn("phase 3a", lower)
        self.assertIn("phase 3b", lower)
        self.assertIn("adr 0003 accepted", lower)
        self.assertIn("state_c_verified", lower)
        self.assertIn("chat=true", lower)
        self.assertIn("structured_json=false", lower)
        self.assertIn("streaming=false", lower)
        self.assertIn("tools=false", lower)
        self.assertIn("multimodal=false", lower)
        self.assertIn("siona_native=false", lower)
        self.assertIn("phase 4 remains **not started**", lower)

    def test_phase3b_planning_and_acceptance_docs_exist(self):
        for path in (
            ROOT / "docs" / "PHASE_3B_HARDWARE_INVENTORY.md",
            ROOT / "docs" / "PHASE_3B_MODEL_INDEPENDENCE.md",
            ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md",
            ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md",
            ROOT / "docs" / "PHASE_3B_ACCEPTANCE.md",
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
        status_block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Accepted (Phase 3B)", status_block)
        self.assertNotRegex(status_block, r"(?m)^\s*Proposed\s*$")
        self.assertIn("llama.cpp b9968 + Qwen3-1.7B-Q4_K_M", adr)
        self.assertIn("not a production-security certification", adr.lower())

    def test_phase3b_official_research_history_preserved(self):
        research = (ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Runtime recommendation history and current status", research)
        self.assertIn("## First-model recommendation history and current status", research)
        self.assertIn("Historical selection status", research)
        self.assertIn("Current status", research)
        self.assertIn("PROVISIONAL — REQUIRED OWNER APPROVAL BEFORE INSTALLATION", research)
        self.assertIn("PROVISIONAL — NO MODEL DOWNLOAD AUTHORIZED AT THE RESEARCH GATE", research)
        self.assertIn("OWNER-AUTHORIZED DOWNLOAD AND PORTABLE INSTALLATION COMPLETED", research)
        self.assertIn("ARTIFACT-VERIFIED LOCALLY", research)
        self.assertIn("RUNTIME CURRENTLY STOPPED", research)
        self.assertIn("CONTROLLED REAL-PROVIDER TEXT PATH VALIDATED", research)
        self.assertIn("STATE C CONTROLLED REGISTRY-BOUND REAL-RUNTIME VERIFICATION PASSED", research)
        self.assertIn("GATE E BREADTH RECORDED", research)
        self.assertIn("llama.cpp native Windows", research)
        self.assertIn("Qwen3-1.7B", research)
        self.assertGreater(research.count("Officially stated"), 10)
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

    def test_phase3b_owner_approved_baseline(self):
        runbook = (ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md").read_text(
            encoding="utf-8"
        )
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        experiment = (ROOT / "docs" / "EXPERIMENT_LOG.md").read_text(encoding="utf-8")
        combined = "\n".join([runbook, status, adr, experiment])
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
        self.assertIn("Quantizer | ggml-org", runbook.replace("`", ""))
        self.assertIn("Accepted (Phase 3B)", adr)
        self.assertIn("Phase 3B is **complete**", status)
        self.assertIn("Phase 4 remains **not started**", status)

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
        self.assertIn("f98e6690faad6a8718451d420a63cbfde6c87028beae4e7f35a36a762730cefd", combined)
        self.assertIn("1282439264", combined)
        self.assertIn("d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5", combined)
        self.assertIn("INSTALLED AND ARTIFACT-VERIFIED LOCALLY; LIMITED LOOPBACK EXECUTION COMPLETED", research)
        self.assertIn("LOCAL SHORT-PROBE OBSERVATION — NOT A PRODUCTION PERFORMANCE CLAIM", experiment)
        self.assertIn("runtime currently **stopped**", status.lower())
        self.assertIn("not listening", status.lower())
        self.assertIn("application-level graceful shutdown", experiment.lower())
        self.assertIn("not verified", experiment.lower())
        self.assertNotIn("```gguf", combined.lower())

    def test_phase3b_real_provider_and_state_c_evidence(self):
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        experiment = (ROOT / "docs" / "EXPERIMENT_LOG.md").read_text(encoding="utf-8")
        runbook = (ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md").read_text(encoding="utf-8")
        gateway = (ROOT / "docs" / "SIONA_MODEL_GATEWAY.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(encoding="utf-8")
        combined = "\n".join([status, experiment, runbook, gateway, adr])

        self.assertIn("EXP-3B-005", experiment)
        self.assertIn("Controlled real SIONA provider validation", experiment)
        self.assertIn("Exact /v1/models model-ID verification succeeded", experiment)
        self.assertIn("LanguageEngine end-to-end used real local provider", experiment)
        self.assertIn("deterministic fallback verified after shutdown", experiment.lower())
        self.assertIn("Structured JSON probe: observed failure", experiment)
        self.assertIn("structured JSON capability remains UNVERIFIED", experiment)
        self.assertIn("EXP-3B-013", combined)
        self.assertIn("STATE C CONTROLLED REGISTRY-BOUND REAL-RUNTIME VERIFICATION PASSED", experiment)
        self.assertIn("runtime currently **stopped**", status.lower())
        self.assertIn("not listening", status.lower())
        self.assertIn("Accepted (Phase 3B)", adr)
        self.assertIn("Phase 3B is **complete**", status)
        self.assertNotIn("production certification is complete", combined.lower())
        self.assertNotIn("broad capabilities are verified", combined.lower())
        self.assertNotIn("structured JSON capability is verified", combined)
        self.assertNotIn("the model is SIONA-native", combined.lower())

    def test_exp3b011_native_json_wording_regression(self):
        docs = [
            ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md",
            ROOT / "docs" / "PHASE_STATUS.md",
            ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md",
            ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md",
            ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md",
            ROOT / "docs" / "PHASE_3B_ACCEPTANCE.md",
            ROOT / "docs" / "SIONA_MODEL_REGISTRY_ACTIVATION_REVIEW.md",
            ROOT / "docs" / "EXPERIMENT_LOG.md",
        ]
        combined = "\n".join(p.read_text(encoding="utf-8") for p in docs)
        self.assertNotIn("Gate E native JSON was separately verified", combined)
        self.assertIn("native json", combined.lower())
        self.assertIn("NOT_VERIFIED", combined)
        self.assertTrue(
            "exact-schema 6/6" in combined
            or "JSON exact-schema 6/6" in combined
            or "exact parsing/schema validation" in combined
            or "six retained Gate E JSON outputs passed exact parsing/schema validation" in combined
        )
        self.assertIn("structured_json=false", combined)
        self.assertIn("streaming=false", combined)
        self.assertIn("State C", combined)
        self.assertIn("Accepted (Phase 3B)", combined)
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("Phase 3B is **complete**", status)
        self.assertIn("Phase 4 remains **not started**", status)

    def test_identity_information_governance_docs(self):
        identity = (ROOT / "docs" / "SIONA_IDENTITY_INFORMATION_GOVERNANCE.md").read_text(encoding="utf-8")
        public = (ROOT / "docs" / "SIONA_PUBLIC_PROFILE_POLICY.md").read_text(encoding="utf-8")
        consent = (ROOT / "docs" / "SIONA_CONSENT_AND_REVOCATION.md").read_text(encoding="utf-8")
        private = (ROOT / "docs" / "SIONA_PRIVATE_CONTEXT_POLICY.md").read_text(encoding="utf-8")
        website = (ROOT / "docs" / "SIONA_WEBSITE_CONTENT_AUDIT_PLAN.md").read_text(encoding="utf-8")
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(encoding="utf-8")

        self.assertIn("SIONA Technologies", identity)
        self.assertIn("Samson Sibona Njaji", identity)
        self.assertIn("James Ndodana Njaji", identity)
        self.assertIn("Co-founder", identity)
        self.assertIn("personal_email: excluded", public)
        self.assertIn("cannot authorize another co-founder's private information", consent.lower())
        self.assertIn("Secrets are never ordinary memory", private)
        self.assertIn("`TRAINING_DATASET` is **denied**", consent)
        self.assertIn("later authorized", website.lower())
        self.assertIn("Do **not** modify the website during this task", website)
        self.assertIn("Phase 3B is **complete**", status)
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertIn("inactive", status.lower())
        self.assertIn("Accepted (Phase 3B)", adr)
        gmail_marker = "@" + "gmail.com"
        for text in (identity, public, consent, private, website):
            self.assertNotIn(gmail_marker, text.lower())

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
