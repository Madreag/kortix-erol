"""
msgspec DTOs for Litestar /v2 API

~65% faster serialization compared to Pydantic.
"""

from typing import Optional, List
from datetime import datetime
import msgspec


class ThreadDTO(msgspec.Struct):
    """Thread data transfer object."""
    id: str
    title: str
    project_id: Optional[str]
    account_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    
    @classmethod
    def from_orm(cls, thread) -> "ThreadDTO":
        return cls(
            id=str(thread.id) if hasattr(thread, 'id') else str(thread.get('thread_id', '')),
            title=thread.title if hasattr(thread, 'title') else thread.get('title', ''),
            project_id=str(thread.project_id) if hasattr(thread, 'project_id') and thread.project_id else thread.get('project_id'),
            account_id=str(thread.account_id) if hasattr(thread, 'account_id') else str(thread.get('account_id', '')),
            created_at=thread.created_at if hasattr(thread, 'created_at') else thread.get('created_at', datetime.utcnow()),
            updated_at=thread.updated_at if hasattr(thread, 'updated_at') else thread.get('updated_at', datetime.utcnow()),
            message_count=len(thread.messages) if hasattr(thread, 'messages') and thread.messages else 0,
        )


class ThreadListDTO(msgspec.Struct):
    """Thread list response."""
    threads: List[ThreadDTO]
    total: int
    page: int
    limit: int


class CreateThreadDTO(msgspec.Struct):
    """Create thread request."""
    title: str
    project_id: Optional[str] = None


class UpdateThreadDTO(msgspec.Struct):
    """Update thread request."""
    title: Optional[str] = None


class ProjectDTO(msgspec.Struct):
    """Project data transfer object."""
    id: str
    name: str
    description: Optional[str]
    account_id: str
    created_at: datetime
    updated_at: datetime
    thread_count: int = 0
    
    @classmethod
    def from_orm(cls, project) -> "ProjectDTO":
        return cls(
            id=str(project.id) if hasattr(project, 'id') else str(project.get('project_id', '')),
            name=project.name if hasattr(project, 'name') else project.get('name', ''),
            description=project.description if hasattr(project, 'description') else project.get('description'),
            account_id=str(project.account_id) if hasattr(project, 'account_id') else str(project.get('account_id', '')),
            created_at=project.created_at if hasattr(project, 'created_at') else project.get('created_at', datetime.utcnow()),
            updated_at=project.updated_at if hasattr(project, 'updated_at') else project.get('updated_at', datetime.utcnow()),
            thread_count=len(project.threads) if hasattr(project, 'threads') and project.threads else 0,
        )


class ProjectListDTO(msgspec.Struct):
    """Project list response."""
    projects: List[ProjectDTO]
    total: int
    page: int
    limit: int


class CreateProjectDTO(msgspec.Struct):
    """Create project request."""
    name: str
    description: Optional[str] = None


class AgentDTO(msgspec.Struct):
    """Agent data transfer object."""
    id: str
    name: str
    description: Optional[str]
    account_id: str
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_orm(cls, agent) -> "AgentDTO":
        return cls(
            id=str(agent.id) if hasattr(agent, 'id') else str(agent.get('agent_id', '')),
            name=agent.name if hasattr(agent, 'name') else agent.get('name', ''),
            description=agent.description if hasattr(agent, 'description') else agent.get('description'),
            account_id=str(agent.account_id) if hasattr(agent, 'account_id') else str(agent.get('account_id', '')),
            created_at=agent.created_at if hasattr(agent, 'created_at') else agent.get('created_at', datetime.utcnow()),
            updated_at=agent.updated_at if hasattr(agent, 'updated_at') else agent.get('updated_at', datetime.utcnow()),
        )


class AgentListDTO(msgspec.Struct):
    """Agent list response."""
    agents: List[AgentDTO]


class ErrorDTO(msgspec.Struct):
    """Error response."""
    detail: str
    code: Optional[str] = None
