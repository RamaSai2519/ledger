"""TransactionParserFallback — spec Part 15.

Interface for a *future* local/on-device ML parser, invoked only when the
deterministic pipeline's confidence is low. No implementation ships here —
this module exists purely to define the contract so the pipeline has
somewhere to plug one in later without a rewrite. Never a cloud LLM: any
implementation must run locally, and its output flows through the exact
same `TransactionValidator`/`ConfidenceScorer` as the deterministic path so
it can never invent a field the validator wouldn't otherwise trust.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from shared.sms.types import ParsedTransaction


class TransactionParserFallback(ABC):
    @abstractmethod
    def parse(self, raw_text: str, sender_id: str, received_at: datetime) -> ParsedTransaction | None:
        """Returns a best-effort ParsedTransaction, or None if it also
        can't confidently parse the message. Must never fabricate a field
        it has no evidence for - the caller re-runs TransactionValidator/
        ConfidenceScorer over whatever this returns."""
        raise NotImplementedError
