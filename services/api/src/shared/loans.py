"""Amortization math for the loans domain (LED-14), mirroring how
shared/recurring.py centralizes cycle-advance math so
jobs/loan_emi_check.py never diverges from any other call site that needs
the same split.

EMI schedules are monthly by convention (unlike recurring_rules, which
supports weekly/monthly/yearly) — a loan's next_due_date always advances by
exactly one calendar month, so this module only needs monthly cycle math,
reusing shared.recurring.advance_due_date("monthly", ...) rather than
reimplementing it.

Standard reducing-balance EMI, simple monthly compounding:
  interest_component = outstanding_balance * (annual_rate / 12 / 100)
  principal_component = emi_amount - interest_component

The final payment is clamped so it never overshoots the outstanding
balance into negative territory: if principal_component would exceed (or
exactly equal) outstanding_balance, that payment pays off exactly
outstanding_balance as principal and the loan is closed.
"""
from dataclasses import dataclass


@dataclass
class EmiSplit:
    interest_component: float
    principal_component: float
    is_final_payment: bool


def compute_emi_split(outstanding_balance: float, annual_interest_rate: float, emi_amount: float) -> EmiSplit:
    """Computes the interest/principal split of the NEXT EMI payment against
    the current outstanding_balance. Clamped so the final payment pays off
    exactly the remaining balance rather than overshooting to a negative
    balance."""
    interest_component = outstanding_balance * (annual_interest_rate / 12 / 100)
    principal_component = emi_amount - interest_component

    if principal_component >= outstanding_balance:
        return EmiSplit(
            interest_component=interest_component,
            principal_component=outstanding_balance,
            is_final_payment=True,
        )

    return EmiSplit(
        interest_component=interest_component,
        principal_component=principal_component,
        is_final_payment=False,
    )
