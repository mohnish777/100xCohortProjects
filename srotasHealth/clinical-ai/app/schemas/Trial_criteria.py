from pydantic import BaseModel
from typing import List


class TrialCriteria(BaseModel):
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]