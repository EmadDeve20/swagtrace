from typing import Any

from pydantic import BaseModel


class Variables(BaseModel):
    headers: dict[str, Any]
    query_params: dict[str, Any]
    body: dict[str, Any]

    # TODO: think about this method more
    # it's depends on out structure
    def normalize_variables(self, func):

        normal_variables = [
            self.headers,
            self.query_params,
            self.body
        ]

        for var in normal_variables:
            var = func(var)
