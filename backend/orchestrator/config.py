"""Pipeline configuration for the multi-agent orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipelineConfig:
    """Configuration for the orchestration pipeline.

    Controls retry behavior, parallelism, validation strictness, and logging.
    """

    max_retries: int = 3
    parallel_limit: int = 3
    checkpoint_strict_mode: bool = True
    log_level: str = "INFO"
    retry_backoff_base: float = 1.0
    request_timeout_seconds: int = 300
    enable_audit_logging: bool = True
