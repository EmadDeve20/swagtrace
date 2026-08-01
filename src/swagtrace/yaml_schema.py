from pydantic import BaseModel, ConfigDict


class Common(BaseModel):
    model_config = ConfigDict(extra="forbid")

class prepareAndFinal(Common):
    execute: str

class ElementInfo(Common):
    method: str
    path: str
    operation_id: str|None
    summary: str|None
    description: str|None
    cases: list

class SwagTaceTestFormat(Common):
    openapi: str
    info: dict
    prepare: prepareAndFinal
    tags: dict[str, list[ElementInfo]]
    final: prepareAndFinal
