import argparse
from swagtrace.initializer import discover_and_save
from swagtrace.recorder import run_server
from swagtrace.tester import run_tests
from swagtrace.consts import DEFAULT_YAML_FILE, DEFAULT_TEST_MODULE_FOLDER
from swagtrace.config import load_config


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
        parents=[common_parser]
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    init_parser = subparsers.add_parser("init", help="initial project")
    init_parser.add_argument("--url", type=str, help="url for openapi.json file", default="http://localhost:8000/openapi.json")
    init_parser.add_argument("-o", "--output", type=str, help="output path for files and folders", default=".")
    init_parser.set_defaults(func=discover_and_save)

    recorder_parser = subparsers.add_parser("record", help="record requests API")
    recorder_parser.add_argument("--host", type=str, help="API Base url", default="http://127.0.0.1:8000")
    recorder_parser.add_argument("--port", type=int, help="Proxy Listen Port", default=8080)
    recorder_parser.add_argument("--file", type=str, help="path of swagtrace.yaml file", default=DEFAULT_YAML_FILE)
    recorder_parser.add_argument("--dir", type=str, help="path of test module", default=DEFAULT_TEST_MODULE_FOLDER)
    recorder_parser.set_defaults(func=run_server)

    tests_parser = subparsers.add_parser("run", help="run tests")
    tests_parser.add_argument("--host", type=str, help="API Base url", default="http://127.0.0.1:8000")
    tests_parser.add_argument("--app", type=str, help="API Base url")
    tests_parser.add_argument("--file", type=str, help="path of swagtrace.yaml file", default=DEFAULT_YAML_FILE)
    tests_parser.add_argument("--dir",  type=str, help="path of test module", default=DEFAULT_TEST_MODULE_FOLDER)
    tests_parser.add_argument("--cases",  nargs="*", help="Name of tags saved in Yaml file", default=[])
    tests_parser.add_argument("--verbose",  action="store_true", help="verbose", default=False)


    
    tests_parser.set_defaults(func=run_tests)


    args = parser.parse_args()

    if hasattr(args, "func"):
        kwargs = {arg[0]:arg[1] for arg in args._get_kwargs() if arg[0] != "command" and arg[0] != "func"} 
        config = kwargs.pop("config")
        load_config(config)
        return args.func(**kwargs)
    else:
        parser.print_help()
