import argparse
from swagtrace.initializer import discover_and_save

def main():
    
    parser = argparse.ArgumentParser(
        prog="swagtrace", 
        description="SwagTrace - API Test Recorder & Runner"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    init_parser = subparsers.add_parser("init", help="initial project")
    init_parser.add_argument("--url", type=str, help="url for openapi.json file", default="http://localhost:8000/openapi.json")
    init_parser.add_argument("-o", "--output", type=str, help="output path for files and folders", default=".")
    init_parser.set_defaults(func=discover_and_save)

    args = parser.parse_args()

    if hasattr(args, "func"):
        kwargs = {arg[0]:arg[1] for arg in args._get_kwargs() if arg[0] != "command" and arg[0] != "func"} 
        args.func(**kwargs)
    else:
        parser.print_help()
