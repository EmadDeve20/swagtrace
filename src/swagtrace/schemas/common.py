from pydantic import BaseModel, ConfigDict


class BaseForbiddenExtraSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

