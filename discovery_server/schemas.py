"""Pydantic schemas for the discovery server."""

from __future__ import annotations

from pydantic import BaseModel


class ServiceInstance(BaseModel):
    """A single service instance in the registry."""

    host: str
    port: int


class RegisterRequest(BaseModel):
    """Request body for POST /register."""

    service_name: str
    host: str
    port: int


class RegisterResponse(BaseModel):
    """Response body for POST /register."""

    status: str
