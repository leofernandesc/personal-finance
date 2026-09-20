from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class IncomingMessage:
    provider: str
    sender_id: str
    external_message_id: str
    text: str


@dataclass(frozen=True)
class OutgoingMessage:
    recipient_id: str
    text: str


class WhatsAppProvider(Protocol):
    """Stable seam between Hermes and a WhatsApp transport."""

    def start(self) -> None: ...

    def send(self, message: OutgoingMessage) -> None: ...

    def stop(self) -> None: ...


class BaileysWhatsAppProvider:
    """Development adapter contract.

    Hermes owns the actual Baileys bridge and invokes registered agent tools.
    Keeping this object transport-agnostic lets a future Cloud API provider
    replace it without changing tools or backend services.
    """

    name = "baileys"

    def start(self) -> None:
        raise RuntimeError(
            "O bridge Baileys é iniciado pelo gateway Hermes. Consulte docs/agent.md."
        )

    def send(self, message: OutgoingMessage) -> None:
        del message
        raise RuntimeError("O envio é realizado pelo adaptador de plataforma do Hermes.")

    def stop(self) -> None:
        return None


class WhatsAppCloudProvider(BaileysWhatsAppProvider):
    """Future placeholder for WhatsApp Business Cloud API."""

    name = "cloud"
