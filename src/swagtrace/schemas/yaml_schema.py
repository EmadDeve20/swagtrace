from .common import BaseForbiddenExtraSchema


class prepareAndFinal(BaseForbiddenExtraSchema):
    execute: str

class TestCase(BaseForbiddenExtraSchema):
    name: str
    request_header: dict
    query_params: dict | None
    request_body: dict | str
    status_code: int
    response_content: str | None

class ElementInfo(BaseForbiddenExtraSchema):
    method: str
    path: str
    operation_id: str|None
    summary: str|None
    description: str|None
    cases: list[TestCase]

class SwagTaceTestFormat(BaseForbiddenExtraSchema):
    openapi: str
    info: dict
    prepare: prepareAndFinal
    tags: dict[str, list[ElementInfo]]
    final: prepareAndFinal

