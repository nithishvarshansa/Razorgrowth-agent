from abc import ABC, abstractmethod
from typing import Any


class GrowthAgentProvider(ABC):
    """Provider boundary for a future LLM; no provider receives credentials."""

    @abstractmethod
    def recommend(self, opportunities: dict[str, Any], analytics: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError


class DeterministicDevelopmentProvider(GrowthAgentProvider):
    """Uses existing deterministic opportunities; it is not an LLM."""

    def recommend(self, opportunities: dict[str, Any], analytics: dict[str, Any]) -> dict[str, Any] | None:
        candidates = opportunities.get("opportunities", [])
        if not isinstance(candidates, list):
            return None
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            required = ("opportunity_type", "customer_id", "recommended_product", "reason", "evidence", "confidence")
            if all(candidate.get(field) for field in required) and isinstance(candidate["evidence"], list):
                return candidate
        return None
