import json
import urllib.error
import urllib.request
from urllib.parse import parse_qsl
import yaml

from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from pathlib import Path

from yaml_syntax.syntax import YamlSyntax

from swagtrace.schemas.yaml_schema import SwagTaceTestFormat, TestCase
from swagtrace.utils import  match_path_template
from swagtrace.consts import TEST_CASE_FORMAT_FILE


# TODO: Use Noise Headers in a config file 
BROWSER_NOISE_HEADERS = {
    "host", "connection", "keep-alive", "proxy-connection", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "user-agent", "accept-language",
    "accept-encoding", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
    "sec-ch-ua-platform-version", "sec-ch-ua-arch", "sec-ch-ua-model",
    "sec-ch-ua-bitness", "sec-ch-ua-full-version", "sec-ch-ua-full-version-list",
    "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user",
    "referer", "origin", "priority", "purpose", "upgrade-insecure-requests",
    "dnt", "sec-gpc", "cache-control", "pragma", "if-none-match", "if-modified-since", "Content-Length",
}

test_file_path:list[Path] = []
test_file_context:list[str] = []

class APIRecorderProxyHandler(BaseHTTPRequestHandler):

    def __init__(self, yaml_syntax:YamlSyntax, host:str, test_module_path:str, *args, **kwargs):
        self.yaml_syntax = yaml_syntax
        self.host = host
        self.test_module_path = Path(test_module_path)

        self.yaml_schema = yaml_syntax.serialized_data

        self.PATH_TO_CASES_MAPPER: dict[str, list[TestCase]] = {
            el.path:el.cases  for _, elements in self.yaml_schema.tags.items() for el in elements
        }
        self.PATH_TO_TAG_MAPPER: dict[str, str] = {
            el.path:tag  for tag, elements in self.yaml_schema.tags.items() for el in elements
        }

        super().__init__(*args, **kwargs)

    def handle_proxy(self):
        method = self.command
        headers = self.headers
        parsed_url = urlparse(self.path)

        actual_path = parsed_url.path
        if not actual_path.startswith("/"):
            actual_path = "/" + actual_path

        query_params = parse_qsl(parsed_url.query)
        if query_params:
            query_params = {query[0]:query[1] for query in query_params}
        else:
            query_params = {}

        content_length = int(headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
        body_str = body_bytes.decode('utf-8', errors='ignore') if body_bytes else ""

        clean_headers = {
            k: v for k, v in headers.items() 
            if k.lower() not in BROWSER_NOISE_HEADERS
        }

        is_api_request = not any(actual_path.endswith(ext) for ext in ['.js', '.css', '.png', '.ico', '.html'])

        matched_template = None
        path_variables = {}

        if actual_path in self.PATH_TO_CASES_MAPPER:
            matched_template = actual_path

        else:
            for template in self.PATH_TO_CASES_MAPPER:
                result = match_path_template(template, actual_path)
                if result is not None:
                    matched_template = template
                    path_variables = result
                    break

        full_path = actual_path
        if parsed_url.query:
            full_path += f"?{parsed_url.query}"

        target_url = f"{self.host}{full_path}"
        forward_headers = {k: v for k, v in headers.items() if k.lower() != 'host'}

        req = urllib.request.Request(
            url=target_url,
            data=body_bytes if body_bytes else None,
            headers=forward_headers,
            method=method
        )

        try:
            with urllib.request.urlopen(req) as response:
                res_status = response.status
                res_headers = response.headers
                res_body = response.read()

                if is_api_request and matched_template is not None:
                    self.captured(
                        method=method,
                        path=matched_template,
                        headers=clean_headers,
                        req_body=body_str,
                        status_code=res_status,
                        res_body_bytes=res_body,
                        path_variables=path_variables,
                        query_params=query_params,
                    )

                self.send_response(res_status)
                for k, v in res_headers.items():
                    if k.lower() not in ['transfer-encoding', 'content-length']:
                        self.send_header(k, v)
                self.send_header('Content-Length', str(len(res_body)))
                self.end_headers()
                self.wfile.write(res_body)


        except urllib.error.HTTPError as e:
            err_body = e.read()
            err_status = e.status

            if is_api_request and matched_template is not None:
                self.captured(
                    method=method,
                    path=matched_template,
                    headers=clean_headers,
                    req_body=body_str,
                    status_code=err_status,
                    res_body_bytes=err_body,
                    path_variables=path_variables,
                    query_params=query_params,
                )
            
            self.send_response(e.code)

            for k, v in e.headers.items():
                if k.lower() not in ['transfer-encoding', 'content-length']:
                    self.send_header(k, v)
            self.send_header('Content-Length', str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)

        except Exception as e:
            self.send_error(502, f"Bad Gateway: Could not connect to {target_url}. Error: {e!s}")

    def captured(self, method, path, headers, req_body, status_code, res_body_bytes, path_variables, query_params):
        print("\n" + "═" * 60)
        print(f"🎯 [CAPTURED API] {method} {path}")
        print("─" * 60)
        
        print("📋 HEADERS:")
        for k, v in headers.items():
            print(f"  {k}: {v}")

        if req_body:
            try:
                req_body = json.loads(req_body)
            except:
                req_body = str(req_body)

            print("─" * 60)
            print("📦 BODY:")
            print(req_body)

        print("─" * 60)
        print("💻 REPRODUCIBLE cURL:")
        curl_headers = " ".join([f"-H '{k}: {v}'" for k, v in headers.items()])
        curl_data = f" -d '{req_body}'" if req_body else ""
        print(f"curl -X '{method}' '{self.host}{path}' {curl_headers}{curl_data}")
        print("─" * 60)
        print(f"Status Code: {status_code}")

        res_body_str = res_body_bytes.decode('utf-8', errors='ignore') if res_body_bytes else ""
        if res_body_str:
            print("📦 RESPONSE BODY:")
            try:
                print(json.dumps(json.loads(res_body_str), indent=2, ensure_ascii=False))
            except Exception:
                print(res_body_str)
        print("═" * 60 + "\n")

        answer_question = input("Do you want to save this case? [Y/n]")

        while answer_question.lower() != "y" and answer_question.lower() != "n" and answer_question != "\n":
            print("Wrong Answer!")
            answer_question = input("Do you want to save this case? [Y/n]")

        if answer_question.lower() == "y" or answer_question == "\n":

            answer_question = input("Also Save Response Content? [Y/n]")

            while answer_question.lower() != "y" and answer_question.lower() != "n" and answer_question != "\n":
                print("Wrong Answer!")
                answer_question = input("Also Save Response Content? [Y/n]")

            if answer_question.lower() == "n":
                res_body_str =  None

            case_name = input("Enter case name: ")
            case_name = case_name.replace(" ", "_")

            case = TestCase(
                name=case_name,
                query_params=query_params,
                request_header=headers,
                request_body=req_body,
                status_code=status_code,
                response_content=res_body_str
            )

            test_tag_folder = self.test_module_path / Path(self.PATH_TO_TAG_MAPPER[path])
            test_tag_folder.mkdir(exist_ok=True)

            init_test_file = test_tag_folder / Path("__init__.py")
            init_test_file.touch()

            test_file_path.append(test_tag_folder / Path(f"{case_name}.py"))

            test_file_context.append(
                TEST_CASE_FORMAT_FILE % {"variables": str(path_variables)}
            )

            self.PATH_TO_CASES_MAPPER[path].append(case)

    def do_CONNECT(self):
        self.send_error(501, "CONNECT method is not supported by this proxy")

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except BrokenPipeError:
            pass
        except ConnectionResetError:
            pass

    do_GET = handle_proxy
    do_POST = handle_proxy
    do_PUT = handle_proxy
    do_DELETE = handle_proxy
    do_PATCH = handle_proxy
    do_HEAD = handle_proxy
    do_OPTIONS = handle_proxy


def run_server(host:str, port:int, file:str, dir:str):
    
    yaml_syntax = YamlSyntax.from_file(SwagTaceTestFormat, file)

    handler_class = partial(
        APIRecorderProxyHandler,
        yaml_syntax,
        host,
        dir
    )

    server_address = ('', port)
    httpd = HTTPServer(server_address, handler_class)
    print(f"🚀 API Recorder Proxy running on http://127.0.0.1:{port}")
    print("🎯 Capturing clean API requests for test replay...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping proxy server...")
        httpd.server_close()

        answer_question = input("Do you want to save all captured cases? [Y/n]")
        while answer_question.lower() != "y" and answer_question.lower() != "n" and answer_question != "\n":
            print("Wrong Answer!")
            answer_question = input("Do you want to save all captured cases? [Y/n]")

        if answer_question.lower() == "n":
            return

        file_address = Path(file)
        with file_address.open("w", encoding="utf-8") as f:
                yaml.dump(yaml_syntax.to_json, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        for file, context in zip(test_file_path, test_file_context):
            file.write_text(context)

