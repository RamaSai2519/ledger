import re

from shared.output import ValidationError

PATCHABLE_FIELDS = {"name", "accent_color"}

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validate(request_json: dict) -> dict:
    if not request_json:
        raise ValidationError("no_fields_to_update")

    updates = {k: v for k, v in request_json.items() if k in PATCHABLE_FIELDS}
    if not updates:
        raise ValidationError("no_recognized_fields_to_update")

    if "name" in updates and not (updates["name"] or "").strip():
        raise ValidationError("name_required")

    if "accent_color" in updates and not HEX_COLOR_RE.match(updates.get("accent_color") or ""):
        raise ValidationError("invalid_accent_color_format")

    return updates
