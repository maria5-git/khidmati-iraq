"""
app/schemas/comment.py
Pydantic v2 schemas for report comments.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserPublic


class CommentCreate(BaseModel):
    content: str = Field(min_length=1)


class CommentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    report_id: int
    author_id: int
    content: str
    is_internal: bool
    created_at: datetime
    author: UserPublic | None = None
