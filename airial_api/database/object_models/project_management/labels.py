# Class definition for Label objects in the database
# Author: Michael B. Lance
#---------------------------------------------------------------------------------------------------------------------------#


from dataclasses import dataclass
from datetime import datetime
from typing import List
from uuid import UUID
from uuid import UUID

from pydantic import BaseModel, field_validator

from ..base import DBbase

#---------------------------------------------------------------------------------------------------------------------------#

@dataclass
class Label(DBbase):
	''' Dataclass for representing labels from the databse
	
	'''
	label_id: int
	schema_id: int
	label: int
	name: str
	image_link: str
	created: datetime
	modified: datetime
	color: str
	uuid: UUID

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def to_dict(self):
		return {
			'label_id': self.label_id,
			'label': self.label,
			'name': self.name,
			'image_link': self.image_link,
			'color': self.color,
			'created': self.fmt_date(self.created),
			'modified': self.fmt_date(self.modified),
			'uuid': str(self.uuid)
		}

#---------------------------------------------------------------------------------------------------------------------------#

class LabelQuery(BaseModel):
	label_id: List[UUID]
		
	@field_validator('label_id', mode='before')
	@classmethod
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		return [value]

