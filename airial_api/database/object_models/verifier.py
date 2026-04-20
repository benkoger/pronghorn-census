from typing import Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, field_validator


class ApproveAnnotationsReq(BaseModel):
    reviewed_area_id: UUID
    image_id: UUID
    annotations: List[Dict]
    deleted_annotations: List[Dict]
