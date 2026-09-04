import inspect
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Command:
    commands: dict[str, list[Callable]]

    def __execute_dependence(self, func: Callable, **kwargs):

        func_sig = inspect.signature(func)

        func_params = func_sig.parameters

        local_kwargs = {key:val for key,val in kwargs.items() if key in func_params}

        func(**local_kwargs)


    def run_command_dependencies(self, command: str, **kwargs):

        dependencies = self.commands.get(command)

        if dependencies is None or len(dependencies) == 0:
            return

        for dep in dependencies:
            self.__execute_dependence(func=dep, **kwargs)
