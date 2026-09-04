from contextvars import ContextVar, Token
from enum import Enum, auto


class TestStatus(Enum):
    idle = auto()
    running = auto()


__runner_context = ContextVar("Runner", default=TestStatus.idle)


def get_runner_status() -> TestStatus:
    return __runner_context.get()


def set_runner_status(status: TestStatus) -> Token:
    return __runner_context.set(status)


def set_running_status_runner() -> Token:
    return set_runner_status(TestStatus.running)


def set_idle_status_runner() -> Token:
    return set_runner_status(TestStatus.idle)


def reset_runner_context(token: Token):
    __runner_context.reset(token)
