# Class definition for Herd Unit objects in the database
# Author: Michael B. Lance
#---------------------------------------------------------------------------------------------------------------------------#

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ..base import DBbase

#---------------------------------------------------------------------------------------------------------------------------#

@dataclass
class HerdUnit(DBbase):
	''' Dataclass for representing Herd Units from the database
	
	'''
	herd_unit_id: int
	name: str
	created: datetime
	modified: datetime
	uuid: UUID

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def to_dict(self):
		return {
			'herd_unit_id': self.herd_unit_id,
			'name': self.name,
			'created': self.fmt_date(self.created),
			'modified': self.fmt_date(self.modified),
			'uuid': str(self.uuid)
		}

#---------------------------------------------------------------------------------------------------------------------------#

class CreateHerdUnitReq(BaseModel):
	name: str
	project_id: UUID