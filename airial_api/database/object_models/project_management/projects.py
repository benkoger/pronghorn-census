# Class definition for Project objects in the database
# Author: Michael B. Lance
#---------------------------------------------------------------------------------------------------------------------------#
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, field_validator

from ..base import DBbase

#---------------------------------------------------------------------------------------------------------------------------#

@dataclass
class Project(DBbase):
	''' Dataclass for representing projects from the databse
	
	'''
	project_id: int
	name: str
	created: datetime
	modified: datetime
	uuid: UUID

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	def to_dict(self):
		return {
			'project_id': self.project_id,
			'name': self.name,
			'created': self.fmt_date(self.created),
			'modified': self.fmt_date(self.modified),
			'uuid': str(self.uuid)
		}

#---------------------------------------------------------------------------------------------------------------------------#

class ProjectQuery(BaseModel):
	project_id: Optional[List[Union[int, UUID]]] = None
		
	@field_validator('project_id', mode='before')
	@classmethod
	def ensure_list(cls, value):
		if isinstance(value, list):
			return value
		return [value]

