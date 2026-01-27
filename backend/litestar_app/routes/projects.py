"""
Projects Controller for Litestar /v2 API

High-performance project endpoints with Redis caching.
"""

from typing import Any
from litestar import Controller, get
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.exceptions import HTTPException

from core.utils.logger import logger
from core.threads import repo as threads_repo
from litestar_app.dtos import ProjectDTO, ProjectListResponse, PaginationDTO


class ProjectsController(Controller):
    """Project endpoints for /v2 API."""
    
    path = "/projects"
    tags = ["projects"]
    
    @get("/", status_code=HTTP_200_OK)
    async def list_projects(
        self,
        current_user: dict[str, Any],
        page: int = 1,
        limit: int = 50,
    ) -> ProjectListResponse:
        """
        List all projects for the authenticated user.
        
        Projects are containers for threads and sandboxes.
        """
        user_id = current_user["user_id"]
        logger.debug(f"[V2] Listing projects for user: {user_id} (page={page}, limit={limit})")
        
        try:
            offset = (page - 1) * limit
            projects, total_count = await threads_repo.list_user_projects(
                user_id, limit, offset
            )
            
            total_pages = (total_count + limit - 1) // limit if total_count else 0
            
            project_dtos = []
            for p in projects:
                sandbox_info = None
                if p.get("sandbox_id"):
                    sandbox_info = {
                        "id": p["sandbox_id"],
                        **(p.get("sandbox_config") or {})
                    }
                
                project_dtos.append(ProjectDTO(
                    project_id=p["project_id"],
                    name=p.get("name") or "",
                    description=p.get("description") or "",
                    is_public=p.get("is_public") or False,
                    icon_name=p.get("icon_name"),
                    created_at=p.get("created_at"),
                    updated_at=p.get("updated_at"),
                    sandbox=sandbox_info,
                ))
            
            return ProjectListResponse(
                projects=project_dtos,
                pagination=PaginationDTO(
                    page=page,
                    limit=limit,
                    total=total_count,
                    pages=total_pages,
                ),
            )
        except Exception as e:
            logger.error(f"[V2] Error listing projects for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")
    
    @get("/{project_id:str}", status_code=HTTP_200_OK)
    async def get_project(
        self,
        project_id: str,
        current_user: dict[str, Any],
    ) -> dict[str, Any]:
        """Get a single project by ID with sandbox details."""
        user_id = current_user["user_id"]
        logger.debug(f"[V2] Getting project {project_id} for user {user_id}")
        
        try:
            project = await threads_repo.get_project_by_id(project_id)
            
            if not project:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Project not found")
            
            # Verify ownership
            if project.get("account_id") != user_id:
                has_access = await threads_repo.check_account_user_access(user_id, project["account_id"])
                if not has_access:
                    raise HTTPException(status_code=403, detail="Not authorized to access this project")
            
            # Build sandbox info
            sandbox_info = {}
            if project.get("sandbox_resource_id"):
                # Get sandbox resource details
                resource = await threads_repo.get_resource_by_id(project["sandbox_resource_id"])
                if resource:
                    sandbox_info = {
                        "id": resource.get("external_id"),
                        **(resource.get("config") or {})
                    }
            
            return {
                "project_id": project["project_id"],
                "account_id": project.get("account_id"),
                "name": project.get("name", ""),
                "description": project.get("description", ""),
                "is_public": project.get("is_public", False),
                "icon_name": project.get("icon_name"),
                "sandbox": sandbox_info,
                "created_at": project.get("created_at"),
                "updated_at": project.get("updated_at"),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[V2] Error getting project {project_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch project: {str(e)}")

