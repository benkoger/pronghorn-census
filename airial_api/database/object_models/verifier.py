"""Pydantic request models for crop verification."""

from uuid import UUID

from pydantic import BaseModel


class ApproveAnnotationsReq(BaseModel):
    """Request model for committing verified and deleted annotations on a crop."""

    reviewed_area_id: UUID
    image_id: UUID
    annotations: list[dict]
    deleted_annotations: list[dict]
