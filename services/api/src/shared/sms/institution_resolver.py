"""InstitutionResolver — spec Part 8.

Combines weighted evidence (sender-ID match, body bank-name/alias mention,
keyword hits, and — via `boost_for_grammar_match` — whether the bank's own
regex grammar actually matched) rather than trusting the sender ID alone.
Reads institution metadata (`institution_name`/`aliases`/`keywords`) added
to the same data-driven `sms_parser_rules` Mongo docs the regex patterns
already live in (CLAUDE.md's "rules editable without a release" constraint
— no separate hardcoded Python registry).
"""
from __future__ import annotations

from shared.sms.sender_resolver import SenderResolver

_SENDER_WEIGHT = 0.60
_BODY_NAME_WEIGHT = 0.90
_KEYWORD_WEIGHT = 0.30
_GRAMMAR_CONFIDENCE = 0.95


class InstitutionResolver:
    def __init__(self, sender_resolver: SenderResolver | None = None):
        self._sender_resolver = sender_resolver or SenderResolver()

    def resolve(self, sender_id: str, normalized_text: str, rules: list[dict]) -> tuple[str | None, float, list[str]]:
        best_bank_code: str | None = None
        best_score = 0.0
        best_evidence: list[str] = []
        lower_text = normalized_text.lower()

        for rule in rules:
            bank_code = rule.get("bank_code")
            if not bank_code or bank_code == "GENERIC":
                continue
            score = 0.0
            evidence: list[str] = []

            if self._sender_resolver.matches(sender_id, rule.get("sender_ids", [])):
                score += _SENDER_WEIGHT
                evidence.append(f"sender ID matches known {bank_code} sender +{_SENDER_WEIGHT}")

            names = [rule.get("institution_name", "")] + rule.get("aliases", [])
            if any(name and name.lower() in lower_text for name in names):
                score += _BODY_NAME_WEIGHT
                evidence.append(f"message body mentions {bank_code} by name +{_BODY_NAME_WEIGHT}")

            if any(keyword and keyword.lower() in lower_text for keyword in rule.get("keywords", [])):
                score += _KEYWORD_WEIGHT
                evidence.append(f"message body matches a {bank_code} keyword +{_KEYWORD_WEIGHT}")

            if score > best_score:
                best_score = score
                best_bank_code = bank_code
                best_evidence = evidence

        return best_bank_code, min(best_score, 0.98), best_evidence

    def boost_for_grammar_match(self, confidence: float, evidence: list[str], bank_code: str) -> tuple[float, list[str]]:
        """Called once the bank's own regex pattern is confirmed to match —
        the strongest evidence per spec Part 8 (+0.95)."""
        boosted = max(confidence, _GRAMMAR_CONFIDENCE)
        return boosted, evidence + [f"{bank_code}'s parser grammar matched the message +{_GRAMMAR_CONFIDENCE}"]
