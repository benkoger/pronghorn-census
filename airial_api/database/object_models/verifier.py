from pydantic import BaseModel, field_validator
from typing import Union, List, Optional, Dict
from uuid import UUID

class ApproveAnnotationsReq(BaseModel):
	reviewed_area_id: Union[int, UUID]
	image_id: Union[int, UUID]
	annotations: List[Dict]
	deleted_annotations: List[Dict]
