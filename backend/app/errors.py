from dataclasses import dataclass
from typing import Optional


@dataclass
class DomainError(Exception):
    status_code: int
    code: str
    message: str
    fields: Optional[dict[str, str]] = None
