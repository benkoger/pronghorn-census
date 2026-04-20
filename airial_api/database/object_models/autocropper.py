from typing import List
from uuid import UUID

from pydantic import BaseModel


class AutoCropperBatchQuery(BaseModel):
    survey_id: UUID
    herd_unit_id: UUID
    model_id: UUID
    label: List[int]
    batch_size: int
    min_confidence: float


class AutoCropReq(BaseModel):
    image_id: UUID
    prediction_ids: List[UUID]
    label_ids: List[UUID]
