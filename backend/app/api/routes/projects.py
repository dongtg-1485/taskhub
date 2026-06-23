from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AsyncSessionDep,
    CurrentUser,
    get_current_active_superuser,
)

from app.schemas.project import (
    CreateProjectRequest,
    ProjectResponse,
)
from app.schemas.task import (
    CreateTaskRequest,
    TaskResponse,
    TasksResponse,
)
from app.repositories import (
    projects,
    tasks,
    workspace_members,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get(
    "/{project_id}/tasks",
    response_model=TasksResponse,
)
async def list_tasks(
    session: AsyncSessionDep,
    current_user: CurrentUser,
    project_id: UUID,
    page: int = 0,
    limit: int = 20,
):
    """
    Lấy danh sách tất cả task trong project.
    """

    # Kiểm tra project có tồn tại không
    project = await projects.get(session, id=project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )
    # Kiểm tra user có phải thành viên của workspace chứa project này không
    member = await workspace_members.get_member(
        session,
        workspace_id=project.workspace_id,
        user_id=current_user.id,
    )
    if not member:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this workspace",
        )
    # Lấy danh sách task
    result = await tasks.list_by_project(session, project_id=project_id, page=page, limit=limit)
    return TasksResponse(
        data=[TaskResponse.model_validate(t) for t in result.items],
        count=result.total,
    )


@router.post(
    "/{project_id}/tasks",
    response_model=TaskResponse,
)
async def create_task(
    session: AsyncSessionDep,
    current_user: CurrentUser,
    project_id: UUID,
    task_in: CreateTaskRequest,
):
    """
    Tạo mới một task trong project.
    """

    # Kiểm tra project có tồn tại không
    project = await projects.get(session, id=project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )
    # Kiểm tra user có phải thành viên của workspace chứa project này không
    member = await workspace_members.get_member(
        session,
        workspace_id=project.workspace_id,
        user_id=current_user.id,
    )
    if not member:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this workspace",
        )
    # Tạo task mới
    data = task_in.model_dump()
    data["project_id"] = project_id
    data["created_by"] = current_user.id
    task = await tasks.create(session, data)
    return TaskResponse.model_validate(task)