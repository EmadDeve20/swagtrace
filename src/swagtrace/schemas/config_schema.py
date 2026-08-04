from typing import Literal

from .common import BaseForbiddenExtraSchema 


class ProjectLogging(BaseForbiddenExtraSchema):
    debug: list[str]
    info: list[str]
    warning: list[str]
    error: list[str]

class Project(BaseForbiddenExtraSchema):
    type :Literal["sync", "async"]
    transport: Literal["asgi", "wsgi"]
    record_target: Literal["yaml", "python"]
    logging: ProjectLogging


class RecorderVariables(BaseForbiddenExtraSchema):
    headers: list[str]
    query_params: list[str]
    body_keys: list[str]

class Recorder(BaseForbiddenExtraSchema):
    header_noise: list[str]
    variables: RecorderVariables

class Config(BaseForbiddenExtraSchema):
    project: Project
    recorder: Recorder

