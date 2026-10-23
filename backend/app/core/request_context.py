from typing import Optional

from starlette.requests import Request


def request_id_from(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)
