from pydantic import BaseModel

class CodeExecutionRequest(BaseModel):
    language: str
    code: str