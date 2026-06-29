from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import (
    AsyncSessionDep,
    CurrentUser,
    RedisDep,
)
from app.core import cache_keys
from app.core.redis import invalidate_by_pattern
from app.models import Message
from app.models.enums import ProjectStatus, TaskPriority, TaskStatus
from app.repositories import (
    projects,
    tasks,
    workspace_members,
)
from app.schemas.project import (
    ProjectResponse,
    ProjectsResponse,
    UpdateProjectRequest,
)
from app.schemas.task import (
    CreateTaskRequest,
    TaskResponse,
    TasksResponse,
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


# ---------------------------------------------------------------------------
# Project CRUD (GET / PATCH / DELETE) + Archive
# ---------------------------------------------------------------------------


async def _get_project_and_check_member(
    session: AsyncSessionDep,
    project_id: UUID,
    user_id: UUID,
) -> tuple:
    """
    Helper: lấy project và kiểm tra user là thành viên workspace.
    Trả về (project, member). Raise 404/403 nếu không hợp lệ.
    """
    project = await projects.get(session, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    member = await workspace_members.get_member(
        session, workspace_id=project.workspace_id, user_id=user_id
    )
    if not member:
        raise HTTPException(
            status_code=403, detail="You are not a member of this workspace."
        )
    return project, member


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    project_id: UUID,
) -> ProjectResponse:
    """
    Lấy thông tin chi tiết của một project. Yêu cầu là thành viên workspace.
    """
    project, _ = await _get_project_and_check_member(
        session, project_id, current_user.id
    )
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}/list", response_model=ProjectsResponse)
async def list_workspace_projects(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    project_id: UUID,
    status: ProjectStatus | None = None,
    page: int = 1,
    limit: int = 20,
) -> ProjectsResponse:
    """
    Lấy danh sách project trong workspace chứa project này.
    Yêu cầu là thành viên workspace.
    """
    project, _ = await _get_project_and_check_member(
        session, project_id, current_user.id
    )
    result = await projects.list_by_workspace(
        session,
        workspace_id=project.workspace_id,
        status=status,
        page=page,
        limit=limit,
    )
    return ProjectsResponse(
        data=[ProjectResponse.model_validate(p) for p in result.items],
        count=result.total,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    project_id: UUID,
    project_in: UpdateProjectRequest,
) -> ProjectResponse:
    """
    Cập nhật thông tin project (name, description).
    Yêu cầu quyền EDITOR trở lên trong workspace.
    """
    from app.models.enums import WorkspaceMemberRole

    project, member = await _get_project_and_check_member(
        session, project_id, current_user.id
    )
    if member.role == WorkspaceMemberRole.VIEWER:
        raise HTTPException(
            status_code=403,
            detail="Yeu cau quyen EDITOR tro len de cap nhat project.",
        )
    updated = await projects.update(
        session, project, project_in.model_dump(exclude_unset=True)
    )
    return ProjectResponse.model_validate(updated)


@router.patch("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    project_id: UUID,
) -> ProjectResponse:
    """
    Archive project (chuyen trang thai thanh ARCHIVED).
    Yeu cau quyen EDITOR tro len trong workspace.
    """
    from app.models.enums import WorkspaceMemberRole

    project, member = await _get_project_and_check_member(
        session, project_id, current_user.id
    )
    if member.role == WorkspaceMemberRole.VIEWER:
        raise HTTPException(
            status_code=403,
            detail="Yeu cau quyen EDITOR tro len de archive project.",
        )
    if project.status == ProjectStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Project da o trang thai ARCHIVED.")
    updated = await projects.update(
        session, project, {"status": ProjectStatus.ARCHIVED}
    )
    return ProjectResponse.model_validate(updated)


@router.patch("/{project_id}/unarchive", response_model=ProjectResponse)
async def unarchive_project(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    project_id: UUID,
) -> ProjectResponse:
    """
    Khoi phuc project tu trang thai ARCHIVED ve ACTIVE.
    Yeu cau quyen EDITOR tro len trong workspace.
    """
    from app.models.enums import WorkspaceMemberRole

    project, member = await _get_project_and_check_member(
        session, project_id, current_user.id
    )
    if member.role == WorkspaceMemberRole.VIEWER:
        raise HTTPException(
            status_code=403,
            detail="Yeu cau quyen EDITOR tro len de unarchive project.",
        )
    if project.status == ProjectStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Project dang o trang thai ACTIVE.")
    updated = await projects.update(session, project, {"status": ProjectStatus.ACTIVE})
    return ProjectResponse.model_validate(updated)


@router.delete("/{project_id}", response_model=Message)
async def delete_project(
    *,
    session: AsyncSessionDep,
    current_user: CurrentUser,
    project_id: UUID,
) -> Message:
    """
    Xoa project va toan bo task, label lien quan.
    Chi OWNER workspace moi co quyen xoa.
    """
    from app.models.enums import WorkspaceMemberRole

    project, member = await _get_project_and_check_member(
        session, project_id, current_user.id
    )
    if member.role != WorkspaceMemberRole.OWNER:
        raise HTTPException(
            status_code=403, detail="Chi OWNER workspace moi co quyen xoa project."
        )
    await projects.delete(session, project)
    return Message(message="Project deleted successfully.")
