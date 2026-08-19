import os
import pathlib

_ENV = pathlib.Path(__file__).resolve().parent / ".env"
if _ENV.exists():
    for line in _ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TIDB_HOST = os.environ["TIDB_HOST"]
TIDB_USER = os.environ["TIDB_USER"]
TIDB_PASSWORD = os.environ["TIDB_PASSWORD"]
TIDB_DB = os.environ.get("TIDB_DB", "airportdb")
TIDB_SSL_CA = os.environ.get("TIDB_SSL_CA", "/etc/ssl/cert.pem")

EMBED_MODEL = "tidbcloud_free/amazon/titan-embed-text-v2"
EMBED_DIM = 1024

AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "sa-east-1")
BEDROCK_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"

TODAY = os.environ.get("DEMO_TODAY", "2015-06-04")


def get_connection():
    import pymysql
    return pymysql.connect(
        host=TIDB_HOST, port=4000, user=TIDB_USER, password=TIDB_PASSWORD,
        database=TIDB_DB, ssl={"ca": TIDB_SSL_CA}, autocommit=True, charset="utf8mb4",
    )


def ask_claude(prompt: str, max_tokens: int = 600) -> str:
    import json
    import boto3
    resp = boto3.client("bedrock-runtime", region_name=AWS_REGION).invoke_model(
        modelId=BEDROCK_MODEL,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    return json.loads(resp["body"].read())["content"][0]["text"]
