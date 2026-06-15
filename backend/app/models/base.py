from sqlalchemy import Column, DateTime, func


def created_at_col() -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def updated_at_col() -> Column:  # type: ignore[type-arg]
    return Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
