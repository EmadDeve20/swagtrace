import argparse

from swagtrace.core import load_commands


def main():

    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--config",
        default="swagtrace.toml",
        help="Path to config file",
    )

    parser = argparse.ArgumentParser(
        prog="swagtrace",
        description="SwagTrace - API Test Recorder & Runner",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    commands = load_commands(subparsers=subparsers)

    args = parser.parse_args()

    if hasattr(args, "func"):
        command = args.command
        kwargs = {
            arg[0]: arg[1]
            for arg in args._get_kwargs()
            if arg[0] != "command" and arg[0] != "func"
        }

        commands.run_command_dependencies(command=command, **kwargs)

        kwargs.pop("config")

        return args.func(**kwargs)
    else:
        parser.print_help()
