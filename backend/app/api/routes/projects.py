from fastapi import APIRouter

from app.schemas.project import (
    CreateProjectRequest,
    ProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get(
    "/",
    response_model=list[ProjectResponse],
)
async def list_projects(
    workspace_id: str,
    page: int = 0,
    limit: int = 20,
):
    """
    Lấy danh sách tất cả project trong workspace.
    """
    # TODO: Implement the logic to fetch projects from the database
    return []