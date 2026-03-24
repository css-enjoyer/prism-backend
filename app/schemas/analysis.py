# Pydantic schemas defiune the shape of data at the API boundary (requests and responses)
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class AnalysisResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  
  id: int
  repo_full_name: str
  pr_number: int
  gh_delivery_id: str
  feedback: dict
  created_at: datetime



