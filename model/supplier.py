from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Supplier:
    id: int | None
    name: str
    nit: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    active: bool = True
