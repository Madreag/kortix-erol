"""
Threads Controller for Litestar /v2 API

High-performance thread endpoints with Redis caching.
"""

from typing import Any, Optional
from litestar import Controller, get, delete
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from litestar.exceptions import HTTPException

from core.utils.logger import logger
from core.threads import repo as threads_repo
from litestar_app.dtos import (
    ThreadDTO, ThreadListResponse, PaginationDTO, ProjectDTO, MessageResponse
)


def _build_project_dto(row: dict[str, Any]) -> Optional[ProjectDTO]:
    """Build ProjectDTO from thread row with project data."""
    if not row.get("project_id"):
        return None
    
    sandbox_info = None
    if row.get("sandbox_id"):
        sandbox_info = {
            "id": row["sandbox_id"],
            **(row.get("sandbox_config") or {})
        }
    
    return ProjectDTO(
        project_id=row["project_id"],
        name=row.get("project_name") or "",
        description=row.get("project_description") or "",
        is_public=row.get("project_is_public") or False,
        icon_name=row.get("project_icon_name"),
        created_at=row.get("project_created_at"),
        updated_at=row.get("project_updated_at"),
        sandbox=sandbox_info,
    )


def _build_thread_dto(row: dict[str, Any]) -> ThreadDTO:
    """Build ThreadDTO from database row."""
    return ThreadDTO(
        thread_id=row["thread_id"],
        project_id=row.get("project_id"),
        name=row.get("name") or "New Chat",
        metadata=row.get("metadata") or {},
        is_public=row.get("is_public") or False,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        project=_build_project_dto(row) if row.get("project_id") else None,
    )


class ThreadsController(Controller):
    """Thread endpoints for /v2 API."""
    
    path = "/threads"
    tags = ["threads"]
    
    @get("/", status_code=HTTP_200_OK)
    async def list_threads(
        self,
        current_user: dict[str, Any],
        page: int = 1,
        limit: int = 100,
    ) -> ThreadListResponse:
        """
        List all threads for the authenticated user.
        
        Cached for 30 seconds per user.
        """
        user_id = current_user["user_id"]
        logger.debug(f"[V2] Listing threads for user: {user_id} (page={page}, limit={limit})")
        
        try:
            offset = (page - 1) * limit
            threads, total_count = await threads_repo.list_user_threads(
                user_id, limit, offset
            )
            
            total_pages = (total_count + limit - 1) // limit if total_count else 0
            
            thread_dtos = [_build_thread_dto(t) for t in threads]
            
            return ThreadListResponse(
                threads=thread_dtos,
                pagination=PaginationDTO(
                    page=page,
                    limit=limit,
                    total=total_count,
                    pages=total_pages,
                ),
            )
        except Exception as e:
            logger.error(f"[V2] Error listing threads for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch threads: {str(e)}")
    
    @get("/{thread_id:str}", status_code=HTTP_200_OK)
    async def get_thread(
        self,
        thread_id: str,
        current_user: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Get a single thread by ID.
        
        Includes project details and recent agent runs.
        """
        user_id = current_user["user_id"]
        logger.debug(f"[V2] Getting thread {thread_id} for user {user_id}")
        
        try:
            thread = await threads_repo.get_thread_with_details(thread_id)
            
            if not thread:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Thread not found")
            
            # Build project data
            project_data = None
            if thread.get("project_id"):
                sandbox_info = {}
                if thread.get("sandbox_external_id"):
                    sandbox_info = {
                        "id": thread.get("sandbox_external_id"),
                        **(thread.get("sandbox_config") or {})
                    }
                
                project_data = {
                    "project_id": thread.get("project_id"),
                    "name": thread.get("project_name", ""),
                    "description": thread.get("project_description", ""),
                    "sandbox": sandbox_info,
                    "is_public": thread.get("project_is_public", False),
                    "icon_name": thread.get("project_icon_name"),
                    "created_at": thread.get("project_created_at"),
                    "updated_at": thread.get("project_updated_at"),
                }
            
            # Get agent runs
            agent_runs_data = await threads_repo.get_thread_agent_runs(thread_id)
            
            return {
                "thread_id": thread["thread_id"],
                "project_id": thread.get("project_id"),
                "name": thread.get("name", "New Chat"),
                "metadata": thread.get("metadata", {}),
                "is_public": thread.get("is_public", False),
                "created_at": thread["created_at"],
                "updated_at": thread["updated_at"],
                "project": project_data,
                "message_count": thread.get("message_count", 0),
                "recent_agent_runs": agent_runs_data,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[V2] Error getting thread {thread_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch thread: {str(e)}")
    
    @delete("/{thread_id:str}", status_code=HTTP_200_OK)
    async def delete_thread(
        self,
        thread_id: str,
        current_user: dict[str, Any],
    ) -> MessageResponse:
        """Delete a thread and optionally its parent project if empty."""
        user_id = current_user["user_id"]
        logger.debug(f"[V2] Deleting thread {thread_id} for user {user_id}")
        
        try:
            # Verify ownership
            thread_account_id = await threads_repo.get_thread_account_id(thread_id)
            if not thread_account_id:
                raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Thread not found")
            
            if thread_account_id != user_id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this thread")
            
            # Get project ID before deletion
            project_id = await threads_repo.get_thread_project_id(thread_id)
            
            # Delete thread and related data
            deleted = await threads_repo.delete_thread_data(thread_id)
            
            if not deleted:
                raise HTTPException(status_code=500, detail="Failed to delete thread")
            
            # Check if project is now empty
            if project_id:
                remaining = await threads_repo.count_project_threads(project_id)
                if remaining == 0:
                    logger.debug(f"[V2] Last thread deleted, cleaning up project {project_id}")
                    await threads_repo.delete_project(project_id)
            
            logger.debug(f"[V2] Successfully deleted thread {thread_id}")
            return MessageResponse(
                message="Thread deleted successfully",
                thread_id=thread_id,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[V2] Error deleting thread {thread_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete thread: {str(e)}")

