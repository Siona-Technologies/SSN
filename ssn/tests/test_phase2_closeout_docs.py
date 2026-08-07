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
            "baseline installed/verified; openai_chat dialect implemented; controlled real-provider text path validated (runtime stopped)",
            text,
        )
        self.assertIn(
            "governed prompt-context bridge merged (EXP-3B-006)",
            text,
        )
        self.assertIn(
            "first approved public identity registry merged (EXP-3B-007)",
            text,
        )
        self.assertIn(
            "controlled real-Qwen governed identity campaign executed (EXP-3B-008",
            text,
        )
        self.assertIn(
            "governed identity response guard implemented and offline-validated with fail-closed hardening (EXP-3B-009",
            text,
        )
        self.assertIn(
            "controlled real-Qwen guarded-path retest executed (EXP-3B-010",
            text,
        )
        self.assertIn(
            "Gate E breadth recorded (EXP-3B-011",
            text,
        )
        self.assertIn(
            "model registry activation, ADR 0003 acceptance and Phase 3B completion decision still pending",
            text,
        )
        self.assertIn("provider", text.lower())
        self.assertIn("openai_chat", text.lower())
        self.assertIn(
            "model registry activation, adr 0003 acceptance and phase 3b completion decision still pending",
            text.lower(),
        )
        self.assertIn("siona_generate", text.lower())
        experiment = (ROOT / "docs" / "EXPERIMENT_LOG.md").read_text(encoding="utf-8")
        self.assertIn("EXP-3B-004", experiment)
        self.assertIn(
            "IMPLEMENTED AND TESTED AGAINST DETERMINISTIC MOCKS",
            experiment,
        )
        self.assertIn("EXP-3B-005", experiment)
        self.assertIn(
            "IMPLEMENTED AND VALIDATED AGAINST THE PINNED LOCAL RUNTIME",
            experiment,
        )
        self.assertIn("LIMITED TEXT-TRANSPORT GATE ONLY", experiment)
        self.assertIn("EXP-3B-006", experiment)
        self.assertIn(
            "IMPLEMENTED AND VALIDATED AGAINST DETERMINISTIC PROVIDERS ONLY",
            experiment,
        )
        self.assertIn("EXP-3B-007", experiment)
        self.assertIn(
            "IMPLEMENTED AND VALIDATED DETERMINISTICALLY",
            experiment,
        )
        self.assertIn("NO AUTOMATIC MODEL INJECTION", experiment)
        self.assertIn("NO ACTIVE PERSONAL RECORDS", experiment)
        self.assertIn("NO MODEL TRAINING", experiment)
        self.assertIn("NO REGISTRY ACTIVATION", experiment)
        self.assertIn("EXP-3B-008", experiment)
        self.assertIn(
            "CAMPAIGN ACCEPTANCE WAS NOT MET",
            experiment,
        )
        self.assertIn("CAPTURED SANITIZED RESPONSE EXCERPTS", experiment)
        self.assertIn("RUNTIME WAS SHUT DOWN AFTER TESTING", experiment)
        self.assertIn("EXP-3B-009", experiment)
        self.assertIn(
            "IMPLEMENTED AND VALIDATED OFFLINE — EXPLICIT GOVERNED IDENTITY RESPONSE",
            experiment,
        )
        self.assertIn("MODEL-NATIVE STRUCTURED JSON REMAINS", experiment)
        self.assertIn("EXP-3B-010", experiment)
        self.assertIn(
            "CONTROLLED REAL LOCAL-MODEL GUARDED-PATH RETEST EXECUTED AGAINST THE",
            experiment,
        )
        self.assertIn(
            "ALL 21 FINAL SIONA-GUARDED RESPONSES PASSED",
            experiment,
        )
        gateway = (ROOT / "docs" / "SIONA_MODEL_GATEWAY.md").read_text(encoding="utf-8")
        self.assertIn("siona_generate", gateway)
        self.assertIn("openai_chat", gateway)
        self.assertIn("EXP-3B-006", gateway)
        self.assertIn("SSN_GOVERNED_CONTEXT", gateway)
        self.assertIn("SSN_LOCAL_MODEL_API_DIALECT", gateway)
        self.assertIn("EXP-3B-005", gateway)
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
        # Research must contain completed comparisons and historical/current status.
        self.assertIn("## Runtime recommendation history and current status", research)
        self.assertIn("## First-model recommendation history and current status", research)
        self.assertIn("Historical selection status", research)
        self.assertIn("Current status", research)
        self.assertIn(
            "PROVISIONAL — REQUIRED OWNER APPROVAL BEFORE INSTALLATION",
            research,
        )
        self.assertIn(
            "PROVISIONAL — NO MODEL DOWNLOAD AUTHORIZED AT THE RESEARCH GATE",
            research,
        )
        self.assertIn(
            "OWNER-AUTHORIZED DOWNLOAD AND PORTABLE INSTALLATION COMPLETED",
            research,
        )
        self.assertIn("ARTIFACT-VERIFIED LOCALLY", research)
        self.assertIn("RUNTIME CURRENTLY STOPPED", research)
        self.assertIn("CONTROLLED REAL-PROVIDER TEXT PATH VALIDATED", research)
        self.assertIn("EXP-3B-005", research)
        self.assertIn("REGISTRY INACTIVE", research)
        self.assertIn("GATE E PENDING", research)
        self.assertIn(
            "Capabilities remain limited/unverified beyond the specific observed text path",
            research,
        )
        self.assertNotIn("PROVIDER INTEGRATION PENDING", research)
        self.assertNotIn("SIONA provider integration has **not** started", research)
        self.assertNotIn(
            "SIONA provider integration | **Pending — not authorized by this update**",
            research,
        )
        self.assertIn("llama.cpp native Windows", research)
        self.assertIn("Qwen3-1.7B", research)
        self.assertNotIn(
            "Do not fill unstable facts from memory",
            research,
        )
        self.assertNotIn(
            "No model download is authorized. No weights have been downloaded.",
            research,
        )
        self.assertNotIn(
            "**Status: PROVISIONAL — NO MODEL DOWNLOAD AUTHORIZED**",
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
        self.assertIn("### Historical pre-install runtime direction", adr)
        self.assertIn("### Historical pre-install model direction", adr)
        self.assertIn("Current local evidence", adr)
        self.assertIn("Controlled real-provider text path", adr)
        self.assertIn("Gate E breadth recorded (EXP-3B-011); registry activation and ADR acceptance still pending", adr)
        self.assertNotIn(
            "### Provisional model direction (not approved / not downloaded)",
            adr,
        )
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
        self.assertIn(
            "capabilities beyond exp-3b-011 gate e results remain conservatively",
            status.lower(),
        )
        self.assertIn("Limited local loopback smoke completed", research)
        self.assertIn(
            "Gate E breadth recorded (EXP-3B-011); registry activation not started",
            research,
        )
        self.assertIn(
            "future governed execution must revalidate required flags before startup",
            research,
        )
        self.assertNotIn(
            "Not evaluated locally — no real-model benchmark completed",
            research,
        )
        self.assertNotIn(
            "before any install approval",
            research,
        )
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

    def test_phase3b_real_provider_validation_evidence(self):
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        experiment = (ROOT / "docs" / "EXPERIMENT_LOG.md").read_text(encoding="utf-8")
        runbook = (ROOT / "docs" / "PHASE_3B_INSTALLATION_RUNBOOK.md").read_text(
            encoding="utf-8"
        )
        gateway = (ROOT / "docs" / "SIONA_MODEL_GATEWAY.md").read_text(encoding="utf-8")
        spec = (ROOT / "docs" / "PHASE_3_ENGINEERING_SPEC.md").read_text(encoding="utf-8")
        research = (ROOT / "docs" / "PHASE_3B_MODEL_RUNTIME_RESEARCH.md").read_text(
            encoding="utf-8"
        )
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        exp005 = experiment.split("### EXP-3B-005", 1)[1] if "### EXP-3B-005" in experiment else ""
        current_docs = "\n".join([status, runbook, gateway, spec, research, adr, exp005])
        combined = "\n".join([status, experiment, runbook, gateway, spec, research, adr])
        self.assertIn("EXP-3B-005", experiment)
        self.assertIn("Controlled real SIONA provider validation", experiment)
        self.assertIn(
            "IMPLEMENTED AND VALIDATED AGAINST THE PINNED LOCAL RUNTIME",
            experiment,
        )
        self.assertIn("LIMITED TEXT-TRANSPORT GATE ONLY", experiment)
        self.assertIn("Controlled real SIONA provider text path validated", research)
        self.assertIn("Exact /v1/models model-ID verification succeeded", experiment)
        self.assertIn(
            "LanguageEngine end-to-end used real local provider",
            experiment,
        )
        self.assertIn("deterministic fallback verified after shutdown", experiment.lower())
        self.assertIn("Structured JSON probe: observed failure", experiment)
        self.assertIn("structured JSON capability remains UNVERIFIED", experiment)
        self.assertIn("Model registry remains inactive", research)
        self.assertIn("Gate E breadth recorded (EXP-3B-011); registry activation remains pending", research)
        self.assertIn("Offline tests 308 passed / 4 skipped", experiment)
        self.assertIn("readiness working-set sample approximately 2.16 GiB", experiment)
        self.assertIn(
            "highest later probe-window sample approximately 1.75 GiB",
            experiment,
        )
        self.assertIn(
            "overall maximum observed across recorded samples approximately 2.16 GiB",
            experiment,
        )
        self.assertIn("real-provider text path", combined.lower())
        self.assertIn("runtime currently **stopped**", status.lower())
        self.assertIn("model registry remains **inactive**", status.lower())
        self.assertIn("inactive", combined.lower())
        self.assertIn("unverified", combined.lower())
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
        adr_status = adr.replace("\r\n", "\n").split("## Status", 1)[1].split(
            "## Context", 1
        )[0]
        self.assertIn("Proposed", adr_status)
        self.assertNotIn("Accepted", adr_status)
        self.assertIn("In progress", status)
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertIn("Controlled real-provider text path validated", runbook)
        self.assertIn("Gate E", runbook)
        self.assertIn("Pending — not complete", runbook)
        # Contradiction guards on current-state docs (exclude older experiment entries).
        self.assertNotIn("SIONA provider integration has not started", current_docs)
        self.assertNotIn("SIONA provider integration has **not** started", current_docs)
        self.assertNotIn("is not wired to this baseline yet", current_docs.lower())
        self.assertNotIn("Provider integration remains outstanding", current_docs)
        self.assertNotIn("PROVIDER INTEGRATION PENDING", research)
        self.assertNotIn("production certification is complete", current_docs.lower())
        self.assertNotIn("broad capabilities are verified", current_docs.lower())
        self.assertNotIn("structured JSON capability is verified", current_docs.lower())
        self.assertNotIn("registry is active", current_docs.lower())
        self.assertNotIn("Phase 3B is complete", current_docs)
        self.assertNotIn("Phase 3B completed", status)
        self.assertNotIn("Phase 4 has started", current_docs)
        self.assertNotIn("the model is SIONA-native", current_docs.lower())
        self.assertNotIn("trained SIONA-native", exp005.lower())
        why = adr.replace("\r\n", "\n").split("### Why ADR status remains Proposed", 1)[1].split(
            "### Conditions", 1
        )[0]
        self.assertIn("Model registry remains inactive", why)
        self.assertIn(
            "Gate E breadth recorded (EXP-3B-011); registry activation and ADR acceptance still pending",
            why,
        )
        self.assertIn(
            "Identity-guard structured JSON remains unverified after EXP-3B-010 observed failure",
            why,
        )
        self.assertIn("Production certification not issued", why)
        self.assertIn("Phase 3B not complete", why)
        self.assertNotIn("not wired to this baseline yet", why)

    def test_identity_information_governance_docs(self):
        identity = (ROOT / "docs" / "SIONA_IDENTITY_INFORMATION_GOVERNANCE.md").read_text(
            encoding="utf-8"
        )
        public = (ROOT / "docs" / "SIONA_PUBLIC_PROFILE_POLICY.md").read_text(encoding="utf-8")
        consent = (ROOT / "docs" / "SIONA_CONSENT_AND_REVOCATION.md").read_text(
            encoding="utf-8"
        )
        private = (ROOT / "docs" / "SIONA_PRIVATE_CONTEXT_POLICY.md").read_text(
            encoding="utf-8"
        )
        website = (ROOT / "docs" / "SIONA_WEBSITE_CONTENT_AUDIT_PLAN.md").read_text(
            encoding="utf-8"
        )
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("SIONA Technologies", identity)
        self.assertIn("Samson Sibona Njaji", identity)
        self.assertIn("James Ndodana Njaji", identity)
        self.assertIn("Co-founder", identity)
        self.assertIn("personal_email: excluded", public)
        self.assertIn(
            "cannot authorize another co-founder's private information",
            consent.lower(),
        )
        self.assertIn("Secrets are never ordinary memory", private)
        self.assertIn("`TRAINING_DATASET` is **denied**", consent)
        self.assertIn("later authorized", website.lower())
        self.assertIn("Do **not** modify the website during this task", website)
        self.assertIn("in progress", status.lower())
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertIn("inactive", status.lower())
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
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
