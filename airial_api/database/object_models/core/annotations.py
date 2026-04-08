# Class definition for Annotation objects in the database
# Author: Michael B. Lance
#---------------------------------------------------------------------------------------------------------------------------#

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ..base import DBbase, Box

#---------------------------------------------------------------------------------------------------------------------------#

@dataclass
class Annotation(DBbase):
	label_id: int
	image_id: int
	herd_unit_id: int
	box_tx: int
	box_ty: int
	box_bx: int
	box_by: int
	annotation_id: int
	created_by_user_id: int
	created: datetime
	modified: datetime
	uuid: UUID
	pred_id: int
	dimensions: 'Box' = field(init=False)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def __post_init__(self):
		self.dimensions = Box((self.box_tx, self.box_ty), (self.box_bx, self.box_by))
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def to_dict(self) -> dict:
		return {
			'annotation_id': self.annotation_id,
			'label_id': self.label_id,
			'image_id': self.image_id,
			'herd_unit_id': self.herd_unit_id,
			'dimensions': self.dimensions.to_dict(),
			'created': self.fmt_date(self.created),
			'modified': self.fmt_date(self.modified),
			'uuid': str(self.uuid)
		}