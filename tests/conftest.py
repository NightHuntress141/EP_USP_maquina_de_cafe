"""Fixtures compartilhadas dos testes da camada de API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Fornece um cliente HTTP de teste para a aplicação FastAPI."""
    return TestClient(app)
