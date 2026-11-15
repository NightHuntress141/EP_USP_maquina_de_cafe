"""Camada de API: controllers, dependências HTTP e roteamento."""

from app.api import client, operator

client_router = client.router
operator_router = operator.router
