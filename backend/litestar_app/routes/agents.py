"""
Agents Controller for Litestar /v2 API

High-performance agent endpoints with Redis caching.
"""

from typing import Any, Optional
from litestar import Controller, get
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.exceptions import HTTPException

from core.utils.logger import logger
from core.agents import repo as agents_repo
from litestar_app.dtos import AgentDTO, AgentListResponse, PaginationDTO


class AgentsController(Controller):
    """Agent endpoints for /v2 API."""
    
    path = "/agents"
    tags = ["agents"]
    
    @get("/", status_code=HTTP_200_OK)
    async def list_agents(
        self,
        current_user: dict[str, Any],
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> AgentListResponse:
        """
        List all agents for the authenticated user.
        
        Supports search, sorting, and pagination.
        """
        user_id = current_user["user_id"]
        logger.debug(f"[V2] Listing agents for user: {user_id} (page={page}, limit={limit})")
        
        try:
            offset = (page - 1) * limit
            agents, total_count = await agents_repo.list_agents(
                account_id=user_id,
                limit=limit,
                offset=offset,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            
            total_pages = (total_count + limit - 1) // limit if total_count else 0
            
            agent_dtos = []
            for a in agents:
                agent_dtos.append(AgentDTO(
                    agent_id=a["agent_id"],
                    name=a.get("name", ""),
                    description=a.get("description"),
                    icon_name=a.get("icon_name"),
                    icon_color=a.get("icon_color"),
                    icon_background=a.get("icon_background"),
                    is_default=a.get("is_default", False),
                    version_count=a.get("version_count", 0),
                    metadata=a.get("metadata") or {},
                    created_at=a.get("created_at"),
                    updated_at=a.get("updated_at"),
                ))
            
            return AgentListResponse(
                agents=agent_dtos,
                pagination=PaginationDTO(
                    page=page,
                    limit=limit,
                    total=total_count,
                    pages=total_pages,
                ),
            )
        except Exception as e:
            logger.error(f"[V2] Error listing agents for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch agents: {str(e)}")
    
    @get("/{agent_id:str}", status_code=HTTP_200_OK)
    async def get_agent(
        self,
        agent_id: str,
        current_user: dict[str, Any],
    ) -> dict[str, Any]:
        """Get a single agent by ID with full configuration."""
        user_id = current_user["user_id"]
        logger.debug(f"[V2] Getting agent {agent_id} for user {user_id}")
        
        try:
            agent = await agents_repo.get_agent_by_id(agent_id, account_id=user_id)
            
            if not agent:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Agent not found")
            
            # Verify ownership
            if agent.get("account_id") != user_id:
                # Check if agent is public
                if not agent.get("is_public", False):
                    raise HTTPException(status_code=403, detail="Not authorized to access this agent")
            
            return {
                "agent_id": agent["agent_id"],
                "account_id": agent.get("account_id"),
                "name": agent.get("name", ""),
                "description": agent.get("description"),
                "icon_name": agent.get("icon_name"),
                "icon_color": agent.get("icon_color"),
                "icon_background": agent.get("icon_background"),
                "is_default": agent.get("is_default", False),
                "is_public": agent.get("is_public", False),
                "tags": agent.get("tags") or [],
                "current_version_id": agent.get("current_version_id"),
                "version_count": agent.get("version_count", 0),
                "metadata": agent.get("metadata") or {},
                "created_at": agent.get("created_at"),
                "updated_at": agent.get("updated_at"),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[V2] Error getting agent {agent_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch agent: {str(e)}")

