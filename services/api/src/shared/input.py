"""Builds a route's `Input` dataclass — the single, uniform way every route
turns a request into a validated dataclass, whether the client-supplied part
comes from a JSON body or query-string args, and regardless of whether the
route also carries URL path params or the JWT identity. No route builds its
Input ad hoc or takes loose positional arguments instead.

Server-populated fields (JWT identity, URL path params, JWT claims) are
passed as keyword arguments and always win — they're never read from the
client-supplied `data` dict, so a client can't spoof its own identity or
another resource's path param by including a same-named key in the JSON
body or query string.

Query-string args can't fill a field named `from` (a Python keyword) — such
fields are declared as `from_` and mapped back to the wire name via
`aliases={"from_": "from"}`.
"""
from dataclasses import fields
from typing import TypeVar

from shared.output import ValidationError

T = TypeVar("T")


def build_input(dataclass_type: type[T], data: dict, aliases: dict[str, str] | None = None, **server_fields) -> T:
    aliases = aliases or {}
    client_field_names = {f.name for f in fields(dataclass_type)} - set(server_fields)
    wire_name = {name: aliases.get(name, name) for name in client_field_names}

    unknown = set(data) - set(wire_name.values())
    if unknown:
        raise ValidationError(f"unknown_field: {sorted(unknown)[0]}")

    kwargs = {name: data[wire] for name, wire in wire_name.items() if wire in data}
    kwargs.update(server_fields)
    return dataclass_type(**kwargs)
