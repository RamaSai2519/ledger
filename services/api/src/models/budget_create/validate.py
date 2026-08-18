from shared.output import ValidationError

BUDGET_SCOPES = {"category", "wallet", "overall"}
BUDGET_PERIODS = {"monthly"}


def validate(inp) -> None:
    if inp.scope not in BUDGET_SCOPES:
        raise ValidationError(f"invalid_budget_scope: {inp.scope}")
    if inp.scope in ("category", "wallet") and not inp.scope_ref_id:
        raise ValidationError(f"scope_ref_id_required_for_scope: {inp.scope}")
    if inp.scope == "overall" and inp.scope_ref_id:
        raise ValidationError("scope_ref_id_must_be_null_for_overall_scope")
    if not isinstance(inp.amount, (int, float)) or inp.amount <= 0:
        raise ValidationError("amount_must_be_positive_number")
    if inp.period not in BUDGET_PERIODS:
        raise ValidationError(f"invalid_budget_period: {inp.period}")
    if inp.threshold_percents is not None:
        if not isinstance(inp.threshold_percents, list) or not inp.threshold_percents:
            raise ValidationError("threshold_percents_must_be_a_non_empty_list")
        for t in inp.threshold_percents:
            if not isinstance(t, (int, float)) or t <= 0:
                raise ValidationError("threshold_percents_must_be_positive_numbers")
