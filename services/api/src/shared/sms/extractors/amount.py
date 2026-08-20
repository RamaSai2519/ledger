"""AmountExtractor — spec Part 5.

Extracts *every* monetary candidate in the SMS first, then classifies each
one by its surrounding context instead of ever assuming "the first number is
the transaction amount". Operates on the normalizer's `RS <amount>` form so
it only needs to match one currency spelling.
"""
from __future__ import annotations

import re

from shared.sms.types import AmountCandidate, FieldValue

# `1,29,999.00` (Indian grouping), `1299.50`, `1,299`, etc. Digits may be
# grouped in 2s after the first group (Indian convention) or ungrouped, so
# this just greedily consumes any digit/comma run and lets `_parse_number`
# strip the commas — an alternation-based "either grouped or ungrouped"
# pattern under-matches (e.g. `\d{1,3}(?:,\d{2,3})*` alone stops at the
# first 3 digits of a 4-digit ungrouped number like "1200").
#
# Real-world finding (LED-18, pulled via scripts/sms_dev from a live
# device): some bank templates (seen from ICICI) never include a Rs./INR/₹
# currency token at all - "...credited with amount 1.75 .Ref..." - so
# "amount <number>" is accepted as a second candidate shape alongside the
# currency-prefixed one, not just as a fallback. The same templates also
# format sub-rupee amounts with no leading digit (".91" instead of "0.91"),
# which `\d[\d,]*` alone can't match since it requires the string to start
# with a digit - the second alternative covers that.
_AMOUNT_RE = re.compile(
    r"(?:RS\s*|\bamount\s+(?:of\s+)?)(?P<amount>\d[\d,]*(?:\.\d{1,2})?|\.\d{1,2})", re.IGNORECASE
)

_WINDOW = 45
# Role-label keywords ("Avl Bal", "Available limit", "Total Due") almost
# always *precede* the amount they describe in real bank SMS, so `before`
# uses the full clipped window; `after` is kept deliberately short so a
# label that's actually describing the *next* amount in the message doesn't
# get attributed backward to this one (e.g. "...at CAFE. Available limit
# INR 48,701" - "Available limit" must attach to 48,701, not the amount
# spent at CAFE just before it).
_AFTER_WINDOW = 20

# Ordered most-specific-first: the first matching role wins. Each entry is
# (role, compiled_keyword_pattern).
_ROLE_KEYWORDS: list[tuple[str, re.Pattern]] = [
    ("minimum_due", re.compile(r"\b(?:min(?:imum)?\.?\s*(?:amt\.?|amount)?\s*due)\b", re.IGNORECASE)),
    ("total_due", re.compile(r"\b(?:total\s*(?:amt\.?|amount)?\s*due)\b", re.IGNORECASE)),
    ("available_credit", re.compile(r"\b(?:avl\.?\s*(?:credit|limit)|available\s+credit)\b", re.IGNORECASE)),
    ("credit_limit", re.compile(r"\bcredit\s*limit\b", re.IGNORECASE)),
    ("available_credit", re.compile(r"\bavailable\s+limit\b", re.IGNORECASE)),
    ("previous_balance", re.compile(r"\bpre(?:vious)?\.?\s*bal(?:ance)?\b", re.IGNORECASE)),
    (
        "available_balance",
        re.compile(r"\b(?:avl\.?\s*bal(?:ance)?|available\s+bal(?:ance)?|current\s+balance|\bbal(?:ance)?\b)\b", re.IGNORECASE),
    ),
]
# Deliberately NOT role-classified here: cashback/refund/emi/fee. In the
# overwhelming majority of real single-amount SMS templates ("Rs.499
# refunded...", "Rs.3200 ... EMI...", "Rs.50 fee debited...") that wording
# describes the *transaction itself* (transaction_type already captures
# refund/emi/fee - see type_detector.py), not a secondary amount alongside
# it, so treating them as a distinct non-transaction role would wrongly
# blank out `amount` for the single most common case. They'd only matter
# for multi-amount statement-style messages, which are handled by
# TransactionType.STATEMENT and never reach this extractor as a
# transaction in the first place.

_TRANSACTION_KEYWORDS = re.compile(
    r"\b(?:debited|withdrawn|spent|paid|charged|deducted|sent|used|credited|received|deposited|added|"
    r"transferred|refunded|reversed)\b",
    re.IGNORECASE,
)


def _parse_number(raw: str) -> float | None:
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


class AmountExtractor:
    def extract_candidates(self, normalized_text: str) -> list[AmountCandidate]:
        candidates: list[AmountCandidate] = []
        for match in _AMOUNT_RE.finditer(normalized_text):
            value = _parse_number(match.group("amount"))
            if value is None:
                continue
            candidates.append(
                AmountCandidate(raw=match.group("amount"), value=value, start=match.start(), end=match.end())
            )

        for i, candidate in enumerate(candidates):
            # Clip each candidate's context window at its neighboring
            # candidates, not just at a fixed character count — otherwise a
            # role keyword that's actually attached to the *next* amount
            # ("Available limit INR 48,701") bleeds backward and
            # misclassifies *this* amount instead (spec Part 5's core
            # requirement: never let one amount's context contaminate
            # another's).
            prev_end = candidates[i - 1].end if i > 0 else 0
            next_start = candidates[i + 1].start if i + 1 < len(candidates) else len(normalized_text)
            window_start = max(0, candidate.start - _WINDOW, prev_end)
            after_end = min(len(normalized_text), candidate.end + _AFTER_WINDOW, next_start)
            before = normalized_text[window_start:candidate.start]
            after = normalized_text[candidate.end:after_end]

            role, evidence = self._classify_role(before, after)
            candidate.role = role
            candidate.role_evidence = evidence
            candidate.role_confidence = 0.9 if role else 0.0

        return candidates

    def _classify_role(self, before: str, after: str) -> tuple[str | None, list[str]]:
        # A role keyword immediately preceding the amount ("Available
        # limit INR 48,701") is much stronger evidence than one merely
        # following it, so `before` is checked first.
        for text in (before, after):
            for role, pattern in _ROLE_KEYWORDS:
                if pattern.search(text):
                    return role, [f"matched \"{pattern.pattern}\" near amount -> {role}"]
        if _TRANSACTION_KEYWORDS.search(before) or _TRANSACTION_KEYWORDS.search(after):
            return "transaction", ["matched debit/credit verb near amount -> transaction"]
        return None, []

    def extract(self, normalized_text: str) -> dict[str, FieldValue]:
        """Returns a dict keyed by role -> FieldValue for every role that was
        confidently identified. `transaction` is the primary transaction
        amount; falls back to the first unclassified/lone candidate only
        when nothing else in the message competed for that role, since a
        single-amount SMS with no other context is still overwhelmingly
        likely to be the transaction amount itself."""
        candidates = self.extract_candidates(normalized_text)
        by_role: dict[str, AmountCandidate] = {}
        for candidate in candidates:
            if candidate.role and candidate.role not in by_role:
                by_role[candidate.role] = candidate

        if "transaction" not in by_role:
            # No candidate had an in-window debit/credit verb, but if
            # exactly one candidate is otherwise unclassified (every other
            # candidate already confidently resolved to balance/limit/due/
            # etc.), it's still overwhelmingly likely to be the transaction
            # amount - e.g. "Your transaction of Rs.300 ... has been
            # reversed. Avl Bal Rs.9000", where "reversed" sits too far
            # from "300" to fall in its keyword window, but "9000" already
            # claimed the available_balance role. Two or more still-
            # unclassified candidates is genuinely ambiguous, so nothing is
            # guessed there (spec Part 13: null over a guess).
            unclassified = [c for c in candidates if c.role is None]
            if len(unclassified) == 1:
                lone = unclassified[0]
                by_role["transaction"] = AmountCandidate(
                    raw=lone.raw,
                    value=lone.value,
                    start=lone.start,
                    end=lone.end,
                    role="transaction",
                    role_confidence=0.55,
                    role_evidence=["only unclassified monetary value in message -> assumed transaction amount"],
                )

        result: dict[str, FieldValue] = {}
        for role, candidate in by_role.items():
            result[role] = FieldValue(
                value=candidate.value, confidence=candidate.role_confidence, evidence=list(candidate.role_evidence)
            )
        return result
