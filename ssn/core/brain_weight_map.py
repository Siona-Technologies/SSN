"""
Brain cognitive weighting profiles for SSN.

Defines how much LLM vs SNN contribute depending on the active brain mode.
"""

WEIGHTS = {
    "deep": {
        "llm": 0.9,
        "snn": 0.1
    },
    "fast": {
        "llm": 0.2,
        "snn": 0.8
    },
    "hybrid": {
        "llm": 0.6,
        "snn": 0.4
    },
    "guest": {
        "llm": 1.0,
        "snn": 0.0
    }
}
