from __future__ import annotations

from fastapi import Request

from app.state import AppContainer


def get_container(request: Request) -> AppContainer:
    return request.app.state.container
