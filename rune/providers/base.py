"""
🔌 RUNE Provider Base — Abstract LLM interface.
All providers implement this interface for unified access.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional


@dataclass
class LLMRequest:
    """Unified request format."""
    prompt: str
    model: str
    system: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 8000
    stream: bool = False


@dataclass
class LLMResponse:
    """Unified response format."""
    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    elapsed_sec: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    def call(self, request: LLMRequest) -> LLMResponse:
        """Send a request and return a response."""
        ...

    @abstractmethod
    def stream(self, request: LLMRequest) -> Iterator[str]:
        """Stream tokens from a request."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display."""
        ...
