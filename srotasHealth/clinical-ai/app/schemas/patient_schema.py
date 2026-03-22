from pydantic import BaseModel, Field
from typing import List, Optional

class Patient(BaseModel):
    age: int = Field(gt=0, lt=170)
    gender: Optional[str]
    conditions: List[str]
    pregnant: Optional[bool] = False