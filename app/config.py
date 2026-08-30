from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    data_dir: Path = ROOT / 'data'
    static_dir: Path = ROOT / 'static'
    fortyguard_api_key: str | None = os.getenv('FORTYGUARD_API_KEY') or None
    openai_api_key: str | None = os.getenv('OPENAI_API_KEY') or None
    openai_model: str = os.getenv('OPENAI_MODEL', 'gpt-5.6')
    allow_live_refresh: bool = os.getenv('ALLOW_LIVE_REFRESH', 'false').lower() == 'true'
    data_mode: str = os.getenv('THERMOCHARGE_DATA_MODE', 'auto').lower()


settings = Settings()
