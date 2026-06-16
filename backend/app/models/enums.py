import enum


class UserRole(str, enum.Enum):
    """
    Vai trò của người dùng trong toàn hệ thống.
    Kế thừa str để giá trị enum có thể so sánh và serialize trực tiếp như string,
    thuận tiện khi lưu vào DB (VARCHAR) và trả về JSON.
    """

    ADMIN = "ADMIN"    # Quản trị viên hệ thống, có toàn quyền
    MEMBER = "MEMBER"  # Thành viên thông thường


class WorkspaceMemberRole(str, enum.Enum):
    """
    Vai trò của thành viên trong một workspace cụ thể.
    Quyền hạn giảm dần: OWNER > EDITOR > VIEWER.
    """

    OWNER = "OWNER"    # Chủ sở hữu workspace, có quyền xóa workspace và quản lý thành viên
    EDITOR = "EDITOR"  # Có quyền tạo/sửa project và task
    VIEWER = "VIEWER"  # Chỉ xem, không thể thay đổi dữ liệu


class ProjectStatus(str, enum.Enum):
    """Trạng thái vòng đời của một project."""

    ACTIVE = "ACTIVE"      # Project đang hoạt động
    ARCHIVED = "ARCHIVED"  # Project đã được lưu trữ, không còn hoạt động


class TaskStatus(str, enum.Enum):
    """
    Trạng thái của một task trong quy trình làm việc (workflow).
    Thứ tự tiến trình thông thường: TODO -> IN_PROGRESS -> IN_REVIEW -> DONE.
    """

    TODO = "TODO"                # Chưa bắt đầu
    IN_PROGRESS = "IN_PROGRESS"  # Đang thực hiện
    IN_REVIEW = "IN_REVIEW"      # Đang được review/kiểm tra
    DONE = "DONE"                # Hoàn thành


class TaskPriority(str, enum.Enum):
    """
    Mức độ ưu tiên của task, dùng để sắp xếp thứ tự xử lý.
    Thứ tự tăng dần: LOW -> MEDIUM -> HIGH -> URGENT.
    """

    LOW = "LOW"        # Ưu tiên thấp
    MEDIUM = "MEDIUM"  # Ưu tiên trung bình (mặc định cho task mới)
    HIGH = "HIGH"      # Ưu tiên cao
    URGENT = "URGENT"  # Khẩn cấp, cần xử lý ngay lập tức
