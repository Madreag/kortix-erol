"""
msgspec DTOs for Litestar /v2 API

High-performance serialization (~65% faster than Pydantic).
Matches existing V1 API response shapes for compatibility.
"""

from datetime import datetime
from typing import Any, Optional
import msgspec


# ============================================================================
# Pagination
# ============================================================================

class PaginationDTO(msgspec.Struct, rename="camel"):
    """Pagination metadata."""
    page: int
    limit: int
    total: int
    pages: int


# ============================================================================
# Sandbox
# ============================================================================

class SandboxDTO(msgspec.Struct, rename="camel"):
    """Sandbox information embedded in projects."""
    id: Optional[str] = None
    vnc_preview: Optional[str] = None
    sandbox_url: Optional[str] = None
    token: Optional[str] = None


# ============================================================================
# Project
# ============================================================================

class ProjectDTO(msgspec.Struct, rename="camel"):
    """Project response DTO."""
    project_id: str
    name: str
    description: str = ""
    is_public: bool = False
    icon_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sandbox: Optional[dict[str, Any]] = None


class ProjectListResponse(msgspec.Struct):
    """Response for listing projects."""
    projects: list[ProjectDTO]
    pagination: PaginationDTO


# ============================================================================
# Thread
# ============================================================================

class ThreadDTO(msgspec.Struct, rename="camel"):
    """Thread response DTO."""
    thread_id: str
    project_id: Optional[str] = None
    name: str = "New Chat"
    metadata: dict[str, Any] = msgspec.field(default_factory=dict)
    is_public: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    project: Optional[ProjectDTO] = None


class ThreadListResponse(msgspec.Struct):
    """Response for listing threads."""
    threads: list[ThreadDTO]
    pagination: PaginationDTO


class ThreadCreateRequest(msgspec.Struct):
    """Request to create a thread."""
    title: Optional[str] = None
    project_id: Optional[str] = None


class ThreadUpdateRequest(msgspec.Struct):
    """Request to update a thread."""
    title: Optional[str] = None
    is_public: Optional[bool] = None


# ============================================================================
# Agent
# ============================================================================

class AgentDTO(msgspec.Struct, rename="camel"):
    """Agent response DTO (list view - minimal fields)."""
    agent_id: str
    name: str
    description: Optional[str] = None
    icon_name: Optional[str] = None
    icon_color: Optional[str] = None
    icon_background: Optional[str] = None
    is_default: bool = False
    version_count: int = 0
    metadata: dict[str, Any] = msgspec.field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentDetailDTO(msgspec.Struct, rename="camel"):
    """Agent response DTO (detail view - full fields)."""
    agent_id: str
    account_id: str
    name: str
    description: Optional[str] = None
    icon_name: Optional[str] = None
    icon_color: Optional[str] = None
    icon_background: Optional[str] = None
    is_default: bool = False
    is_public: bool = False
    tags: list[str] = msgspec.field(default_factory=list)
    current_version_id: Optional[str] = None
    version_count: int = 0
    metadata: dict[str, Any] = msgspec.field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentListResponse(msgspec.Struct):
    """Response for listing agents."""
    agents: list[AgentDTO]
    pagination: PaginationDTO


# ============================================================================
# Generic Response
# ============================================================================

class MessageResponse(msgspec.Struct):
    """Generic message response."""
    message: str
    thread_id: Optional[str] = None
    project_id: Optional[str] = None

