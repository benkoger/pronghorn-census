# Class definition for Survey objects in the database
# Author: Michael B. Lance
#---------------------------------------------------------------------------------------------------------------------------#

from dataclasses import dataclass
from datetime import datetime
from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from ..base import DBbase

#---------------------------------------------------------------------------------------------------------------------------#

@dataclass
class Survey(DBbase):
	''' Dataclass for representing Surveys from the database
	
	'''
	survey_id: int
	survey_date: datetime
	name: str
	additional_info: str
	created: datetime
	modified: datetime
	uuid: UUID

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def to_dict(self):
		return {
			'survey_id': self.survey_id,
			'survey_date': self.survey_date,
			'name': self.name,
			'additional_info': self.additional_info,
			'created': self.fmt_date(self.created),
			'modified': self.fmt_date(self.modified),
			'uuid': str(self.uuid)
		}
	

#---------------------------------------------------------------------------------------------------------------------------#

class CreateSurveyReq(BaseModel):
    project_id: Union[int, UUID]
    herd_unit_ids: List[Union[int, UUID]]
    survey_date: datetime
    name: str
    additional_info: Optional[str]

#---------------------------------------------------------------------------------------------------------------------------#

class UpdateSurveyReq(BaseModel):
    survey_date: Optional[datetime] = None
    name: Optional[str] = None
    additional_info: Optional[str] = None 