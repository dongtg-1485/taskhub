from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import (
    AsyncSessionDep,
    CurrentUser,
    RedisDep,
)
from app.core import cache_keys
from app.core.redis import invalidate_by_pattern
from app.models import (
    Message,
)
from app.schemas.task import (
    UpdateTaskRequest,
    TaskResponse,
)
from app.repositories import (
    projects,
    tasks,
    workspace_members,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
async def update_task(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    redis: RedisDep,
    task_id: UUID,
    task_update: UpdateTaskRequest,
) -> TaskResponse:
    """
    Cập nhật thông tin của một task.
    """
    # Kiểm tra task có tồn tại không
    task = await tasks.get(session, id=task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )
    # Lấy project để lấy workspace_id (tránh lazy-load relationship trong async context)
    project = await projects.get(session, id=task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
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
    
    # Cập nhật task
    data = task_update.model_dump(exclude_unset=True)
    updated_task = await tasks.update(session, db_obj=task, data=data)

    # Invalidate toàn bộ cache danh sách task của project này
    await invalidate_by_pattern(redis, cache_keys.task_list_pattern(task.project_id))

    return TaskResponse.model_validate(updated_task)


@router.delete(
    "/{task_id}",
    response_model=Message,
)
async def delete_task(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    redis: RedisDep,
    task_id: UUID,
) -> Message:
    """
    Xóa một task.
    """
    # Kiểm tra task có tồn tại không
    task = await tasks.get(session, id=task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )
    # Lấy project để lấy workspace_id (tránh lazy-load relationship trong async context)
    project = await projects.get(session, id=task.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
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
    
    # Lưu project_id trước khi xóa để dùng cho cache invalidation
    project_id = task.project_id

    # Xóa task
    await tasks.delete(session, db_obj=task)

    # Invalidate toàn bộ cache danh sách task của project này
    await invalidate_by_pattern(redis, cache_keys.task_list_pattern(project_id))

    return Message(message="Task deleted successfully")