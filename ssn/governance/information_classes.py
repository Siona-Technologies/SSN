"""Information classification enums for SIONA identity governance."""

from __future__ import annotations

from enum import Enum


class InformationClass(str, Enum):
    PUBLIC_COMPANY = "PUBLIC_COMPANY"
    PUBLIC_PROFESSIONAL = "PUBLIC_PROFESSIONAL"
    OWNER_PRIVATE = "OWNER_PRIVATE"
    COFOUNDER_PRIVATE = "COFOUNDER_PRIVATE"
    COMPANY_CONFIDENTIAL = "COMPANY_CONFIDENTIAL"
    LEGAL_RESTRICTED = "LEGAL_RESTRICTED"
    SECRET = "SECRET"
    FORGET_DELETE = "FORGET_DELETE"


class ApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class SubjectType(str, Enum):
    COMPANY = "COMPANY"
    PRODUCT = "PRODUCT"
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PROJECT = "PROJECT"


class AllowedUse(str, Enum):
    PUBLIC_WEBSITE = "PUBLIC_WEBSITE"
    PUBLIC_RESPONSE = "PUBLIC_RESPONSE"
    OWNER_ASSISTANCE = "OWNER_ASSISTANCE"
    INTERNAL_OPERATIONS = "INTERNAL_OPERATIONS"
    LEGAL_WORKFLOW = "LEGAL_WORKFLOW"
    RETRIEVAL = "RETRIEVAL"
    MODEL_PROMPT = "MODEL_PROMPT"
    RECORD_APPROVAL = "RECORD_APPROVAL"
    TRAINING_DATASET = "TRAINING_DATASET"


# Higher rank = stricter. Derived summaries inherit the maximum rank.
_CLASSIFICATION_RANK = {
    InformationClass.PUBLIC_COMPANY: 10,
    InformationClass.PUBLIC_PROFESSIONAL: 20,
    InformationClass.OWNER_PRIVATE: 40,
    InformationClass.COFOUNDER_PRIVATE: 50,
    InformationClass.COMPANY_CONFIDENTIAL: 60,
    InformationClass.LEGAL_RESTRICTED: 70,
    InformationClass.SECRET: 90,
    InformationClass.FORGET_DELETE: 100,
}


def classification_rank(cls: InformationClass | None) -> int:
    if cls is None:
        return 10_000  # missing classification is fail-closed / stricter than all
    return _CLASSIFICATION_RANK[cls]
