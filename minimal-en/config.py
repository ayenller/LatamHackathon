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

# Two interchangeable answering models. Bedrock is the default; set
# GEMINI_API_KEY (Google AI Studio) instead if you have no Bedrock access.
# LLM_PROVIDER forces one when both are configured.
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "sa-east-1")
BEDROCK_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER") or ("gemini" if GEMINI_API_KEY else "bedrock")

TODAY = os.environ.get("DEMO_TODAY", "2015-06-04")


def get_connection():
    import pymysql
    return pymysql.connect(
        host=TIDB_HOST, port=4000, user=TIDB_USER, password=TIDB_PASSWORD,
        database=TIDB_DB, ssl={"ca": TIDB_SSL_CA}, autocommit=True, charset="utf8mb4",
    )


def ask_claude(prompt: str, max_tokens: int = 600) -> str:
    """Send one prompt to whichever provider is configured, return the text."""
    if LLM_PROVIDER == "gemini":
        return _ask_gemini(prompt, max_tokens)
    return _ask_bedrock(prompt, max_tokens)


def _ask_bedrock(prompt: str, max_tokens: int) -> str:
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


_GEMINI_CLIENT = None


def _gemini_client():
    """Cached on purpose. The client owns an HTTP connection and closes it when
    it is collected, so a throwaway `genai.Client(...).models...` can have its
    transport shut from under the in-flight request."""
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        from google import genai
        if not GEMINI_API_KEY:
            raise RuntimeError("LLM_PROVIDER=gemini but GEMINI_API_KEY is not set")
        _GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
    return _GEMINI_CLIENT


def _ask_gemini(prompt: str, max_tokens: int) -> str:
    from google.genai import types
    resp = _gemini_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            # Gemini reasons by default and those tokens count against
            # max_output_tokens, which can leave no budget for the answer.
            # Gemini 3 takes a level here; thinking_budget=0 is rejected.
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        ),
    )
    return resp.text or ""
