import inspect

from functools import wraps
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Awaitable

from swagtrace.utils import function_manager


class BaseMockInterface(ABC):

    @abstractmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError


class MockInterface(BaseMockInterface):

    def __init__(self,
                 data:Any|None=None,
                 *args,
                 exception:object|None=None,
                 side_effect:Callable|Coroutine|Awaitable|None=None,
                 **kwargs):

        self.__validate(side_effect)
        self.exception = exception
        self.data = data
        self.side_effect = side_effect
        self.__args = args
        self.__kwargs = kwargs


    def __validate(self, side_effect:Callable|Coroutine|Awaitable|None):
        if (
            not callable(side_effect)
            and side_effect is not None
            and not inspect.isawaitable(side_effect)
        ):
            raise ValueError("side_effect must be callable or just awaitable")

        return side_effect


    def execute(self, *args, **kwargs):

        if self.exception:
            raise self.exception

        elif self.side_effect:
            if args or kwargs:
                return function_manager.get_function_address(self.side_effect, *args, **kwargs) 

            return function_manager.get_function_address(self.side_effect, *self.__args, **self.__kwargs) 

        return self.data



class mock:

    def __init__(self, mock_interface:BaseMockInterface):

        self.mock_interface = mock_interface

    # TODO: Update all wrappers to run mock_interface if swagger run tests
    def __call__(self, func, *args, **kwargs):

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if True:
                return function_manager.get_function_address(func, *args, **kwargs)

            return function_manager.get_function_address(self.mock_interface.execute, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if True:
                return function_manager.get_function_address(func, *args, **kwargs)

            return function_manager.get_function_address(self.mock_interface.execute, *args, **kwargs)

        wrapper = async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

        wrapper.mock_data = self.mock_data

        return wrapper


    def mock_data(self, *args, **kwargs):
        return function_manager.get_function_address(self.mock_interface.execute, *args, **kwargs)
