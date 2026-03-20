from typing import List, Optional, Union
from uuid import UUID

from pydantic import BaseModel

class SetActiveOrg(BaseModel):
	org_id: Union[int, UUID]