from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    AsyncSessionDep,
    CurrentUser,
    RedisDep,
)
from app.core import cache_keys
from app.core.redis import invalidate_by_pattern
from app.models.enums import TaskPriority, TaskStatus
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
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    redis: RedisDep,
    project_id: UUID,
    page: int = 0,
    limit: int = 20,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: UUID | None = None,
) -> TasksResponse:
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

    # Tạo cache key riêng cho từng tổ hợp filter/phân trang
    base_key = cache_keys.task_list(project_id)
    cache_key = (
        f"{base_key}"
        f":page={page}:limit={limit}"
        f":status={status}:priority={priority}:assignee={assignee_id}"
    )

    # Đọc từ cache trước
    cached = await redis.get(cache_key)
    if cached:
        return TasksResponse.model_validate_json(cached)

    # Cache miss — truy vấn DB
    result = await tasks.list_by_project(
        session,
        project_id=project_id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        page=page,
        limit=limit,
    )
    response = TasksResponse(
        data=[TaskResponse.model_validate(t) for t in result.items],
        count=result.total,
        page=result.page,
        limit=result.limit,
        pages=result.pages,
    )

    # Lưu vào cache với TTL ngắn (danh sách task thay đổi thường xuyên)
    await redis.set(cache_key, response.model_dump_json(), ex=cache_keys.TTL_SHORT)

    return response


@router.post(
    "/{project_id}/tasks",
    response_model=TaskResponse,
)
async def create_task(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    redis: RedisDep,
    project_id: UUID,
    task_in: CreateTaskRequest,
) -> TaskResponse:
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

    # Invalidate toàn bộ cache danh sách task của project này
    await invalidate_by_pattern(redis, cache_keys.task_list_pattern(project_id))

    return TaskResponse.model_validate(task)