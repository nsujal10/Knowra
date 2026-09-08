from pydantic import BaseModel, ConfigDict

class BaseSchema(BaseModel):
    """Shared base for all Pydantic v2 schemas."""
    model_config = ConfigDict(from_attributes=True)