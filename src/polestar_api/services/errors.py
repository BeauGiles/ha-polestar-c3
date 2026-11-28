"""Chronos error stream: charging and climate timer changes the car couldn't apply."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from .. import grpc as grpc_call
from ..models.chronos_errors import ChronosErrors
from .chronos import wrap_chronos

if TYPE_CHECKING:
    from ..connection import GrpcConnection


class ErrorServiceClient:
    def __init__(self, connection: GrpcConnection, vin: str) -> None:
        self._connection = connection
        self._vin = vin

    async def stream(self) -> AsyncIterator[ChronosErrors]:
        """Subscribe to ``ErrorService/GetErrors``. It stays silent until an error happens, then sends one message."""
        metadata = await self._connection.get_metadata(self._vin)
        metadata["vin"] = self._vin
        async for data in grpc_call.unary_stream(
            self._connection.channel,
            f"{self._connection.backend.error_svc}/GetErrors",
            wrap_chronos(self._vin),
            metadata=metadata,
        ):
            if data:
                yield ChronosErrors.from_bytes(data)
