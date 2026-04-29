# Class definition for Schema objects in the database
# Author: Michael B. Lance
#---------------------------------------------------------------------------------------------------------------------------#

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..base import DBbase

#---------------------------------------------------------------------------------------------------------------------------#

@dataclass
class Schema(DBbase):
	''' Dataclass for representing scehmas from the databse
	
	'''
	schema_id: int
	name: str
	created: datetime
	modified: datetime
	uuid: UUID

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def to_dict(self):
		return {
			'schema_id': self.schema_id,
			'name': self.name,
			'created': self.fmt_date(self.created),
			'modified': self.fmt_date(self.modified),
			'uuid': str(self.uuid)
		}