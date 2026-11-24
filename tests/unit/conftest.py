from __future__ import annotations

import socket

import pytest


@pytest.fixture(autouse=True)
def kein_netz(monkeypatch):
    """Unit-Tests dürfen niemals echte Verbindungen oder DNS-Aufrufe machen."""

    def blockiert(*args, **kwargs):
        raise AssertionError("Netzwerkzugriff in Unit-Tests blockiert")

    monkeypatch.setattr(socket.socket, "connect", blockiert)
    monkeypatch.setattr(socket.socket, "connect_ex", blockiert)
    monkeypatch.setattr(socket, "getaddrinfo", blockiert)
    monkeypatch.setattr(socket, "create_connection", blockiert)
