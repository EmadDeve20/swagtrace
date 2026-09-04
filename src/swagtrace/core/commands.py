from argparse import _SubParsersAction
from collections.abc import Callable

from swagtrace.schemas.commands import Command
from swagtrace.shared import load_config

from .initializer import set_initializer_command
from .recorder import set_recorder_command
from .tester import set_tester_command


def load_commands(subparsers: _SubParsersAction) -> Command:

    commands: dict[str, list[Callable]] = {}

    init_command = set_initializer_command(subparsers=subparsers)
    commands[init_command] = []

    recorder_command = set_recorder_command(subparsers=subparsers)
    commands[recorder_command] = [load_config]

    tester_command = set_tester_command(subparsers=subparsers)
    commands[tester_command] = [load_config]

    return Command(commands=commands)
