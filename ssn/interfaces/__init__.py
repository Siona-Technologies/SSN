# ssn/interfaces/__init__.py

"""
SSN interfaces package.

Important:
- Do NOT import gateway/handlers here.
- Keep __init__ side-effect free to prevent circular imports.
"""

__all__ = []
# ssn/interfaces/__init__.py
from .front_door import handle_user_message
