from models.budget_create.validate import BUDGET_SCOPES
from shared.output import ValidationError


def validate(query) -> None:
    if query.scope is not None and query.scope not in BUDGET_SCOPES:
        raise ValidationError(f"invalid_budget_scope: {query.scope}")
