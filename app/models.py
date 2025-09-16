from pydantic import BaseModel
from typing import List, Optional
from sqlmodel import SQLModel, Field
import json

# ----- Incoming JSON schemas -----
class JobRole(BaseModel):
    id: str
    title: str
    description: str
    department: Optional[str] = None
    skills: List[str] = []
    level: Optional[str] = None
    updated_at: Optional[str] = None

class ProcessStep(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    depends_on: List[str] = []

class ProcessFlow(BaseModel):
    id: str
    name: str
    steps: List[ProcessStep]
    owner: Optional[str] = None
    updated_at: Optional[str] = None

class UploadPayload(BaseModel):
    job_roles: Optional[List[JobRole]] = None
    process_flows: Optional[List[ProcessFlow]] = None

# ----- Database models -----
class JobRoleRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    title: str
    description: str
    department: Optional[str] = None
    skills_json: str
    level: Optional[str] = None
    updated_at: Optional[str] = None

class ProcessStepRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    description: Optional[str] = None

class ProcessFlowRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    owner: Optional[str] = None
    updated_at: Optional[str] = None

class ProcessFlowStepRow(SQLModel, table=True):
    flow_id: str = Field(primary_key=True)
    step_id: str = Field(primary_key=True)
    depends_on_json: str

def skills_to_json(skills: list[str]) -> str:
    return json.dumps(skills)

def deps_to_json(deps: list[str]) -> str:
    return json.dumps(deps)
