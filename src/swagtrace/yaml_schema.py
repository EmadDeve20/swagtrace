from pydantic import BaseModel, ConfigDict


class Common(BaseModel):
    model_config = ConfigDict(extra="forbid")

class prepareAndFinal(Common):
    execute: str

class TestCase(Common):
    name: str
    request_header: dict
    query_params: dict | None
    request_body: dict | str
    status_code: int
    response_content: str | None

class ElementInfo(Common):
    method: str
    path: str
    operation_id: str|None
    summary: str|None
    description: str|None
    cases: list[TestCase]

class SwagTaceTestFormat(Common):
    openapi: str
    info: dict
    prepare: prepareAndFinal
    tags: dict[str, list[ElementInfo]]
    final: prepareAndFinal

