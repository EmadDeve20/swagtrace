import json
import urllib.error
import urllib.request
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from pathlib import Path
import yaml


from yaml_syntax.syntax import YamlSyntax

from swagtrace.consts import DEFAULT_YAML_FILE
from swagtrace.yaml_schema import SwagTaceTestFormat, TestCase

TARGET_HOST = "http://127.0.0.1:8000"
LISTEN_PORT = 8080

LOCAL_IDENTIFIERS = ['localhost', '127.0.0.1', '0.0.0.0']

BROWSER_NOISE_HEADERS = {
    "host", "connection", "keep-alive", "proxy-connection", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "user-agent", "accept-language",
    "accept-encoding", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
    "sec-ch-ua-platform-version", "sec-ch-ua-arch", "sec-ch-ua-model",
    "sec-ch-ua-bitness", "sec-ch-ua-full-version", "sec-ch-ua-full-version-list",
    "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user",
    "referer", "origin", "priority", "purpose", "upgrade-insecure-requests",
    "dnt", "sec-gpc", "cache-control", "pragma", "if-none-match", "if-modified-since",
}

class APIRecorderProxyHandler(BaseHTTPRequestHandler):

    def __init__(self, yaml_syntax:YamlSyntax, *args, **kwargs):
        self.yaml_syntax = yaml_syntax

        self.yaml_schema = yaml_syntax.serialized_data

        self.PATH_TO_CASES_MAPPER: dict[str, list[TestCase]] = {
            el.path:el.cases  for _, elements in self.yaml_schema.tags.items() for el in elements
        }

        super().__init__(*args, **kwargs)

    def handle_proxy(self):
        method = self.command
        headers = self.headers


        parsed_url = urlparse(self.path)
        clean_path = parsed_url.path
        if parsed_url.query:
            clean_path += f"?{parsed_url.query}"
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path

        content_length = int(headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
        body_str = body_bytes.decode('utf-8', errors='ignore') if body_bytes else ""

        clean_headers = {
            k: v for k, v in headers.items() 
            if k.lower() not in BROWSER_NOISE_HEADERS
        }

        is_api_request = not any(clean_path.endswith(ext) for ext in ['.js', '.css', '.png', '.ico', '.html'])


        target_url = f"{TARGET_HOST}{clean_path}"
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
                if is_api_request and clean_path in self.PATH_TO_CASES_MAPPER:
                    self.captured(
                                    method=method,
                                    path=clean_path,
                                    headers=clean_headers,
                                    req_body=body_str,
                                    status_code=res_status,
                                    res_body_bytes=res_body
                                )

                self.send_response(res_status)
                for k, v in res_headers.items():
                    if k.lower() not in ['transfer-encoding', 'content-length']:
                        self.send_header(k, v)
                self.send_header('Content-Length', str(len(res_body)))
                self.end_headers()
                self.wfile.write(res_body)


        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            err_body = e.read()
            for k, v in e.headers.items():
                if k.lower() not in ['transfer-encoding', 'content-length']:
                    self.send_header(k, v)
            self.send_header('Content-Length', str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)

        except Exception as e:
            self.send_error(502, f"Bad Gateway: Could not connect to {target_url}. Error: {e!s}")

    def captured(self, method, path, headers, req_body, status_code, res_body_bytes):
        print(f"{self.PATH_TO_CASES_MAPPER=}")
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
        print(f"curl -X '{method}' '{TARGET_HOST}{path}' {curl_headers}{curl_data}")
        print("─" * 60)
        print(f"Status Code: {status_code}")

        body_str = res_body_bytes.decode('utf-8', errors='ignore') if res_body_bytes else ""
        if body_str:
            print("📦 RESPONSE BODY:")
            try:
                print(json.dumps(json.loads(body_str), indent=2, ensure_ascii=False))
            except Exception:
                print(body_str)
        print("═" * 60 + "\n")

        case_name = input("Enter case name: ")
        case_name = case_name.replace(" ", "_")

        case = TestCase(
            name=case_name,
            request_header=headers,
            request_body=req_body,
            status_code=status_code
        )

        self.PATH_TO_CASES_MAPPER[path].append(case)

        print(f"{self.PATH_TO_CASES_MAPPER=}")
        print(f"{self.yaml_schema.tags["Accounting"][0].cases=}")
        

    do_GET = handle_proxy
    do_POST = handle_proxy
    do_PUT = handle_proxy
    do_DELETE = handle_proxy
    do_PATCH = handle_proxy
    do_HEAD = handle_proxy
    do_OPTIONS = handle_proxy


def run_server(host:str, port:int, file_address:str = DEFAULT_YAML_FILE):
    yaml_syntax = YamlSyntax.from_file(SwagTaceTestFormat, DEFAULT_YAML_FILE)

    handler_class = partial(
        APIRecorderProxyHandler,
        yaml_syntax
    )

    server_address = ('', LISTEN_PORT)
    httpd = HTTPServer(server_address, handler_class)
    print(f"🚀 API Recorder Proxy running on http://127.0.0.1:{LISTEN_PORT}")
    print("🎯 Capturing clean API requests for test replay...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping proxy server...")
        httpd.server_close()
        file_address = Path(file_address)
        with file_address.open("w", encoding="utf-8") as f:
                yaml.dump(yaml_syntax.to_json, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


if __name__ == "__main__":
    run_server("http://127.0.0.1:8000", 8080, DEFAULT_YAML_FILE)

