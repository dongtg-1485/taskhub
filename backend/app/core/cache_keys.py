"""
Quản lý cache key tập trung cho toàn bộ ứng dụng.

Quy tắc đặt tên key:
  {entity}:{id}                  — chi tiết một object (detail)
  {entity}:list:{scope}:{id}     — danh sách object thuộc một scope cụ thể

Ví dụ:
  task:a1b2c3d4-...              — chi tiết task
  task:list:project:e5f6g7h8-..  — danh sách task của project
  project:list:workspace:...     — danh sách project của workspace

Tất cả route thực hiện cache/invalidation đều import hàm từ module này,
không được tự khai báo key string riêng.
"""

from uuid import UUID

# ---------------------------------------------------------------------------
# TTL mặc định (giây)
# ---------------------------------------------------------------------------

TTL_SHORT: int = 60  # 1 phút — dữ liệu thay đổi thường xuyên (danh sách task, comment)
TTL_MEDIUM: int = 300  # 5 phút — dữ liệu ít thay đổi (project, label)
TTL_LONG: int = 3600  # 1 giờ — dữ liệu gần như bất biến (workspace detail)


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


def workspace_detail(workspace_id: UUID) -> str:
    """Chi tiết một workspace."""
    return f"workspace:{workspace_id}"


def workspace_list(user_id: UUID) -> str:
    """Danh sách workspace mà user là thành viên."""
    return f"workspace:list:user:{user_id}"


def workspace_members(workspace_id: UUID) -> str:
    """Danh sách thành viên của một workspace."""
    return f"workspace:members:{workspace_id}"


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


def project_detail(project_id: UUID) -> str:
    """Chi tiết một project."""
    return f"project:{project_id}"


def project_list(workspace_id: UUID) -> str:
    """Danh sách project thuộc một workspace."""
    return f"project:list:workspace:{workspace_id}"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


def task_detail(task_id: UUID) -> str:
    """Chi tiết một task."""
    return f"task:{task_id}"


def task_list(project_id: UUID) -> str:
    """Danh sách task thuộc một project."""
    return f"task:list:project:{project_id}"


def task_list_pattern(project_id: UUID) -> str:
    """Pattern glob để xóa toàn bộ cache danh sách task của một project (mọi filter/phân trang)."""
    return f"task:list:project:{project_id}:*"


# ---------------------------------------------------------------------------
# Label
# ---------------------------------------------------------------------------


def label_list(project_id: UUID) -> str:
    """Danh sách label thuộc một project."""
    return f"label:list:project:{project_id}"


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------


def comment_list(task_id: UUID) -> str:
    """Danh sách comment thuộc một task."""
    return f"comment:list:task:{task_id}"
