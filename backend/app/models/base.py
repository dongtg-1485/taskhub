from sqlalchemy import Column, DateTime, func


def created_at_col() -> Column:  # type: ignore[type-arg]
    """
    Factory trả về SQLAlchemy Column dùng cho trường 'created_at'.

    - DateTime(timezone=True): Lưu timestamp có timezone (TIMESTAMPTZ trong PostgreSQL).
      Dùng timezone=True để tránh nhập nhằng khi so sánh thời gian giữa các timezone khác nhau.
    - server_default=func.now(): Giá trị mặc định được DB tự set lúc INSERT (không qua Python).
      Dùng server_default thay vì default của Python để đảm bảo tính nhất quán ngay cả khi
      record được insert thẳng vào DB không qua ORM.
    - nullable=False: Trường bắt buộc phải có giá trị, không cho phép NULL.
    """
    return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def updated_at_col() -> Column:  # type: ignore[type-arg]
    """
    Factory trả về SQLAlchemy Column dùng cho trường 'updated_at'.

    - DateTime(timezone=True): Tương tự created_at, lưu timestamp có timezone.
    - server_default=func.now(): Tự động set khi INSERT lần đầu.
    - onupdate=func.now(): Tự động cập nhật timestamp mỗi khi row được UPDATE qua ORM.
    - nullable=False: Luôn có giá trị, không cho phép NULL.
    """
    return Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
