from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Task(BaseModel):
    session_id: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    payload: Optional[str]
