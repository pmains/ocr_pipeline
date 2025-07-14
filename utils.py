import yaml
from pathlib import Path
from functools import lru_cache

from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

import os

DEFAULT_CONFIG_PATH = (Path(__file__).parent.parent / "config.yaml").resolve()
DEFAULT_PAGE_BREAK_PATTERN = r"\s*--- PAGE BREAK ---\s*"

LANG_CODE_TO_NAME = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ca": "Catalan",
    "la": "Latin",
    "pt": "Portuguese",
    "gr": "Greek",
    # Add more as needed
}

@lru_cache(maxsize=1)
def get_config(config_path=None):
    config_path = Path(config_path or DEFAULT_CONFIG_PATH)
    if not config_path.exists():
        raise FileNotFoundError(f"❌ Config file not found at {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_api_key():
    config = get_config()
    if "openai_api_key" not in config:
        raise ValueError("❌ OpenAI API key not configured in config.yaml")
    return config.get("openai_api_key", None)


def get_poppler_path():
    config = get_config()
    poppler_path = config.get("poppler_path", None)
    if not poppler_path:
        raise ValueError("❌ Poppler path not configured in config.yaml")
    return Path(poppler_path).resolve()


def get_tesseract_path():
    config = get_config()
    tesseract_path = config.get("tesseract_path", None)
    if not tesseract_path:
        raise ValueError("❌ Tesseract path not configured in config.yaml")
    return Path(tesseract_path).resolve()


def call_gpt(text, prompt):
    client = OpenAI(api_key=get_api_key())
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            ChatCompletionSystemMessageParam(role="system", content=prompt),
            ChatCompletionUserMessageParam(role="user", content=text)
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content