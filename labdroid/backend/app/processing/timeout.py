from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar


T = TypeVar("T")


async def run_with_timeout(coro: Awaitable[T], timeout_s: float, message: str) -> T:
    try:
        return await asyncio.wait_for(coro, timeout=timeout_s)
    except asyncio.TimeoutError as exc:
        raise TimeoutError(message) from exc
