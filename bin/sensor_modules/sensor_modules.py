#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import http.client
import urllib.parse

def load_config(env_name: str) -> dict:
    env_name_lower = env_name.lower()
    config_file = Path(__file__).parent / f".env.{env_name_lower}"
    if not config_file.exists():
        print(f"sensor_modules: Config not found: {config_file}", file=sys.stderr)
        sys.exit(1)

    config = {}
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, val = line.split('=', 1)
            config[key] = val
    return config

def parse_url(url: str) -> tuple:
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme
    host = parsed.netloc
    path = parsed.path
    if parsed.query:
        path += "?" + parsed.query
    return scheme, host, path

def http_request(method: str, url: str, auth_header: str = None, body: bytes = None, content_type: str = None) -> bytes:
    scheme, host, path = parse_url(url)

    conn_class = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
    conn = conn_class(host)

    headers = {
        "User-Agent": "sensor-modules-client/1.0",
    }

    if auth_header:
        headers["Authorization"] = auth_header

    if content_type:
        headers["Content-Type"] = content_type
    elif method == "POST" and body:
        headers["Content-Type"] = "application/json"

    if body:
        headers["Content-Length"] = str(len(body))

    try:
        conn.request(method, path, body, headers)
        response = conn.getresponse()
        data = response.read()
        status = response.status

        if status >= 400:
            print(f"HTTP {status}: {response.reason}", file=sys.stderr)
            if data:
                try:
                    print(data.decode('utf-8', errors='ignore'), file=sys.stderr)
                except:
                    pass
            sys.exit(1)

        return data
    finally:
        conn.close()

def login(env_name: str) -> str:
    """ログインして JWT Bearer トークンを取得"""
    config = load_config(env_name)

    login_payload = {
        "customerId": config["LOGIN_CUSTOMER"],
        "userId": config["LOGIN_USER"],
        "password": config["LOGIN_PASSWORD"]
    }

    url = config["AUTH_BASE"] + "/api/v1/login"
    body = json.dumps(login_payload).encode()

    response_data = http_request("POST", url, body=body)

    try:
        response_json = json.loads(response_data)
        token = response_json.get("sessionToken")
        if not token:
            print("sensor_modules: No sessionToken in login response", file=sys.stderr)
            sys.exit(1)
        return token
    except json.JSONDecodeError:
        print("sensor_modules: Invalid JSON in login response", file=sys.stderr)
        sys.exit(1)

def list_modules(env_name: str):
    token = login(env_name)
    config = load_config(env_name)
    auth = f"Bearer {token}"
    url = config["API_BASE"] + "/api/v1/modules"

    data = http_request("GET", url, auth)

    try:
        modules = json.loads(data)
        print(json.dumps(modules, ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        sys.stdout.buffer.write(data)

def put_module(env_name: str, module_type: str, version: str, sensor_id: str = None, chip_type: str = None, dry_run: bool = False):
    config = load_config(env_name)

    # dry_run の場合はログインをスキップ
    if not dry_run:
        token = login(env_name)
    else:
        token = "<token>"

    auth = f"Bearer {token}"
    url = config["API_BASE"] + "/api/v1/modules"

    # stdin からバイナリを読み込み
    binary = sys.stdin.buffer.read()

    # info JSON を作成
    info_dict = {
        "moduleType": module_type,
        "version": int(version),
    }
    if sensor_id:
        info_dict["sensorId"] = sensor_id
    if chip_type:
        info_dict["chipType"] = chip_type

    info_json = json.dumps(info_dict)

    if dry_run:
        print("=== DRY RUN MODE ===", file=sys.stderr)
        print(f"URL: {url}", file=sys.stderr)
        print(f"Auth: Bearer <token>", file=sys.stderr)
        print(f"Binary size: {len(binary)} bytes", file=sys.stderr)
        print(f"Info JSON:", file=sys.stderr)
        print(json.dumps(info_dict, indent=2), file=sys.stderr)
        print("", file=sys.stderr)
        print("(実際のアップロードは実行されませんでした)", file=sys.stderr)
        return

    # multipart/form-data を構築
    boundary = "----SensorModulesBoundary"
    body = bytearray()

    # info フィールド
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="info"\r\n')
    body.extend(b'Content-Type: application/json\r\n\r\n')
    body.extend(info_json.encode())
    body.extend(b'\r\n')

    # binary フィールド
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="binary"; filename="module.zip"\r\n')
    body.extend(b'Content-Type: application/octet-stream\r\n\r\n')
    body.extend(binary)
    body.extend(b'\r\n')

    # 終了境界
    body.extend(f"--{boundary}--\r\n".encode())

    content_type = f"multipart/form-data; boundary={boundary}"
    http_request("POST", url, auth, bytes(body), content_type)
    print("Module uploaded successfully", file=sys.stderr)

def get_module(env_name: str, module_id: str):
    token = login(env_name)
    config = load_config(env_name)
    auth = f"Bearer {token}"
    url = config["SENSOR_BASE"] + f"/api/v1/modules/{module_id}"

    data = http_request("GET", url, auth)
    sys.stdout.buffer.write(data)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: sensor_modules.py list <env>", file=sys.stderr)
        print("       sensor_modules.py get <env> <moduleId>", file=sys.stderr)
        print("       sensor_modules.py put [--dry-run] <env> <moduleType> <version> [sensorId] [chipType]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        if len(sys.argv) != 3:
            print("sensor_modules.py: Too few arguments", file=sys.stderr)
            sys.exit(1)
        list_modules(sys.argv[2])
    elif command == "get":
        if len(sys.argv) != 4:
            print("sensor_modules.py: Too few arguments", file=sys.stderr)
            sys.exit(1)
        get_module(sys.argv[2], sys.argv[3])
    elif command == "put":
        dry_run = False
        args_start = 2

        if len(sys.argv) > 2 and sys.argv[2] == "--dry-run":
            dry_run = True
            args_start = 3

        if len(sys.argv) < args_start + 3:
            print("sensor_modules.py: Too few arguments", file=sys.stderr)
            sys.exit(1)

        env_name = sys.argv[args_start]
        module_type = sys.argv[args_start + 1]
        version = sys.argv[args_start + 2]
        sensor_id = sys.argv[args_start + 3] if len(sys.argv) > args_start + 3 else None
        chip_type = sys.argv[args_start + 4] if len(sys.argv) > args_start + 4 else None

        put_module(env_name, module_type, version, sensor_id, chip_type, dry_run)
    else:
        print(f"sensor_modules.py: Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
