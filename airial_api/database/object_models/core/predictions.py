# Class definition for Prediction objects in the database
# Author: Michael B. Lance
#---------------------------------------------------------------------------------------------------------------------------#
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, field_validator

from ..base import Box, DBbase

#---------------------------------------------------------------------------------------------------------------------------#

@dataclass
class Prediction(DBbase):
	pred_id: int
	image_id: int
	model_id: int
	label: int
	score: float
	box_tx: int
	box_ty: int
	box_bx: int
	box_by: int
	created: datetime | None
	reviewed_by_user_id: int
	uuid: UUID
	dimensions: 'Box' = field(init=False)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def __post_init__(self):
		self.dimensions = Box((self.box_tx, self.box_ty), (self.box_bx, self.box_by))

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def to_dict(self) -> dict:
		return {
			"pred_id": self.pred_id,
			"score": self.score,
			"dimensions": self.dimensions.to_dict(),
			# ... etc
		}

#---------------------------------------------------------------------------------------------------------------------------#

class PredictionQuery(BaseModel):
	prediction_id: List[UUID]

	@field_validator('prediction_id')
	@classmethod 
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		if value is None or value == '':
			return []
		return [value]

#---------------------------------------------------------------------------------------------------------------------------#

class CreatePredictionReq(BaseModel):
	image_id: UUID
	model_id: UUID
	label: int 
	score: float 
	box_tx: int 
	box_ty: int
	box_bx: int
	box_by: int
	

