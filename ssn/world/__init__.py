# ssn/world/__init__.py
"""
SSN World Model (Phase 5.5)

Maintains SSN's internal belief state ("what is happening") in a bounded,
time-aware, confidence-driven representation.

This is the foundation for Jarvis-like situation awareness:
- entities (people/objects/zones)
- events (motion, presence, alerts)
- decay/TTL to keep state fresh and bounded
"""
