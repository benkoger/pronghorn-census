from pydantic import BaseModel
from typing import Optional, Union, List
from datetime import datetime
from uuid import UUID

class Authenticate(BaseModel):
	external_id: str