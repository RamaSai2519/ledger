from shared.output import ValidationError


def validate(inp) -> None:
    if not inp.order or not isinstance(inp.order, list):
        raise ValidationError("order_required")
    if any(not isinstance(cid, str) or not cid for cid in inp.order):
        raise ValidationError("invalid_category_id_in_order")
    if len(set(inp.order)) != len(inp.order):
        raise ValidationError("duplicate_category_id_in_order")
