import enum
from sqlalchemy import Enum


def str_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Store enums as VARCHAR + CHECK constraint so new values only need a migration, not a type change."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


def money(value) -> float:
    """Serialize NUMERIC money for the existing JSON API, which uses numbers."""
    return float(value) if value is not None else 0.0


def ev(value):
    """Enum value for API output; tolerates plain strings assigned before a refresh."""
    return value.value if isinstance(value, enum.Enum) else value
