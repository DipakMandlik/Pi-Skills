"""
Content Safety Moderation Layer - AI-powered content filtering
Detects harmful, inappropriate, or policy-violating content
"""
from __future__ import annotations

import logging
import re
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("backend.content_safety")


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ModerationResult:
    risk_level: RiskLevel
    flags: list[str]
    categories: dict[str, float]
    safe: bool
    action: str
    details: dict


class ContentSafetyEngine:
    def __init__(self):
        self.blocked_patterns = [
            (r'(?i)(password|secret|api.?key|token)\s*[:=]\s*\S+', "SENSITIVE_DATA"),
            (r'(?i)(ssn|social.?security|credit.?card)\s*[:=]?\s*\d{3}[-\s]?\d{2}[-\s]?\d{4}', "PII"),
            (r'(?i)\b(drop|delete|truncate|alter)\s+(table|database|schema)\b', "SQL_INJECTION"),
            (r'(?i)(rm\s+-rf|sudo\s+rm|format\s+c:)', "DANGEROUS_COMMAND"),
            (r'(?i)(exec|eval|system)\s*\(', "CODE_INJECTION"),
        ]

        self.warning_patterns = [
            (r'(?i)(hack|exploit|vulnerability|backdoor)', "SECURITY_TOPIC"),
            (r'(?i)(illegal|piracy|crack|keygen)', "LEGAL_CONCERN"),
            (r'(?i)(hate|violence|harassment|discriminat)', "HARMFUL_CONTENT"),
        ]

        self.prompt_injection_patterns = [
            (r'(?i)ignore\s+(all\s+)?(previous|above|prior)\s+instructions', "INSTRUCTION_OVERRIDE"),
            (r'(?i)you\s+are\s+now\s+(a\s+)?(different|new|jailbreak)', "ROLE_HIJACK"),
            (r'(?i)pretend\s+(you\s+)?(don.?t|do\s+not)\s+have\s+(any\s+)?(rules|restrictions|guidelines)', "RESTRICTION_BYPASS"),
            (r'(?i)disregard\s+(all\s+)?(safety|content|ethical)\s+(guidelines|filters|rules)', "SAFETY_BYPASS"),
            (r'(?i)act\s+as\s+(a\s+)?(unrestricted|unfiltered|uncensored)', "UNCENSORED_MODE"),
            (r'(?i)my\s+previous\s+instructions?\s+(were|are)\s+wrong', "CONTEXT_MANIPULATION"),
            (r'(?i)system\s*prompt\s*[:=]\s*', "SYSTEM_PROMPT_INJECTION"),
        ]

        self.forbidden_topics = [
            "weapons制造",
            "drug合成",
            "explosive制造",
            "malware开发",
        ]

    def moderate_prompt(
        self,
        prompt: str,
        user_id: Optional[str] = None,
        strict_mode: bool = False,
    ) -> ModerationResult:
        flags = []
        categories: dict[str, float] = {}
        risk_scores: list[float] = []

        for pattern, category in self.prompt_injection_patterns:
            if re.search(pattern, prompt):
                flags.append(category)
                categories[category] = 1.0
                risk_scores.append(1.0)

        for pattern, category in self.blocked_patterns:
            if re.search(pattern, prompt):
                flags.append(category)
                categories[category] = 0.9
                risk_scores.append(0.9)

        for pattern, category in self.warning_patterns:
            matches = re.findall(pattern, prompt)
            if matches:
                flags.append(category)
                categories[category] = 0.5
                risk_scores.append(0.5)

        prompt_lower = prompt.lower()
        for topic in self.forbidden_topics:
            if topic.lower() in prompt_lower:
                flags.append("FORBIDDEN_TOPIC")
                categories["FORBIDDEN_TOPIC"] = 1.0
                risk_scores.append(1.0)

        if len(prompt) > 100000:
            flags.append("EXCESSIVE_LENGTH")
            categories["EXCESSIVE_LENGTH"] = 0.7
            risk_scores.append(0.7)

        max_risk = max(risk_scores) if risk_scores else 0
        risk_level = self._calculate_risk_level(max_risk, flags)

        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            action = "block"
        elif risk_level == RiskLevel.MEDIUM:
            action = "warn" if not strict_mode else "block"
        elif risk_level == RiskLevel.LOW:
            action = "allow"
        else:
            action = "allow"

        return ModerationResult(
            risk_level=risk_level,
            flags=flags,
            categories=categories,
            safe=action == "allow",
            action=action,
            details={
                "prompt_length": len(prompt),
                "word_count": len(prompt.split()),
                "max_risk_score": round(max_risk, 2),
                "flag_count": len(flags),
                "strict_mode": strict_mode,
            },
        )

    def moderate_response(
        self,
        response: str,
        user_id: Optional[str] = None,
    ) -> ModerationResult:
        flags = []
        categories: dict[str, float] = {}
        risk_scores: list[float] = []

        for pattern, category in self.blocked_patterns:
            if re.search(pattern, response):
                flags.append(f"RESPONSE_{category}")
                categories[f"RESPONSE_{category}"] = 0.9
                risk_scores.append(0.9)

        for pattern, category in self.warning_patterns:
            if re.search(pattern, response):
                flags.append(f"RESPONSE_{category}")
                categories[f"RESPONSE_{category}"] = 0.5
                risk_scores.append(0.5)

        hallucination_indicators = [
            r'(?i)as\s+an\s+ai\s+language\s+model',
            r'(?i)i\s+cannot\s+(access|browse|visit)\s+(the\s+)?(internet|web)',
            r'(?i)my\s+knowledge\s+cutoff',
        ]

        for pattern in hallucination_indicators:
            if re.search(pattern, response):
                flags.append("AI_DISCLOSURE")
                categories["AI_DISCLOSURE"] = 0.2
                risk_scores.append(0.2)

        max_risk = max(risk_scores) if risk_scores else 0
        risk_level = self._calculate_risk_level(max_risk, flags)

        return ModerationResult(
            risk_level=risk_level,
            flags=flags,
            categories=categories,
            safe=risk_level in [RiskLevel.SAFE, RiskLevel.LOW],
            action="allow" if risk_level in [RiskLevel.SAFE, RiskLevel.LOW] else "flag",
            details={
                "response_length": len(response),
                "word_count": len(response.split()),
            },
        )

    def sanitize_prompt(self, prompt: str) -> str:
        sanitized = prompt

        for pattern, _ in self.prompt_injection_patterns:
            sanitized = re.sub(pattern, "[REMOVED]", sanitized)

        for pattern, _ in self.blocked_patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized)

        return sanitized

    def get_content_policy(self) -> dict:
        return {
            "blocked_categories": [
                {"name": "SENSITIVE_DATA", "description": "API keys, passwords, tokens"},
                {"name": "PII", "description": "Social security numbers, credit cards"},
                {"name": "SQL_INJECTION", "description": "SQL injection attempts"},
                {"name": "DANGEROUS_COMMAND", "description": "Destructive shell commands"},
                {"name": "CODE_INJECTION", "description": "Code injection attempts"},
            ],
            "warning_categories": [
                {"name": "SECURITY_TOPIC", "description": "Security-related discussions"},
                {"name": "LEGAL_CONCERN", "description": "Potentially illegal content"},
                {"name": "HARMFUL_CONTENT", "description": "Hate speech or harassment"},
            ],
            "injection_categories": [
                {"name": "INSTRUCTION_OVERRIDE", "description": "Attempts to override instructions"},
                {"name": "ROLE_HIJACK", "description": "Attempts to change AI role"},
                {"name": "RESTRICTION_BYPASS", "description": "Attempts to bypass restrictions"},
                {"name": "SAFETY_BYPASS", "description": "Attempts to bypass safety filters"},
            ],
            "actions": {
                "block": "Request is blocked and not processed",
                "warn": "Request is allowed with a warning",
                "allow": "Request passes moderation",
                "flag": "Response is flagged for review",
            },
        }

    def _calculate_risk_level(
        self,
        max_risk: float,
        flags: list[str],
    ) -> RiskLevel:
        prompt_injection_flags = [
            "INSTRUCTION_OVERRIDE", "ROLE_HIJACK", "RESTRICTION_BYPASS",
            "SAFETY_BYPASS", "UNCENSORED_MODE", "CONTEXT_MANIPULATION",
            "SYSTEM_PROMPT_INJECTION", "FORBIDDEN_TOPIC",
        ]

        if any(f in prompt_injection_flags for f in flags):
            return RiskLevel.CRITICAL

        if max_risk >= 0.9:
            return RiskLevel.HIGH
        elif max_risk >= 0.7:
            return RiskLevel.MEDIUM
        elif max_risk >= 0.4:
            return RiskLevel.LOW
        else:
            return RiskLevel.SAFE


content_safety = ContentSafetyEngine()
