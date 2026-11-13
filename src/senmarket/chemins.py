from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("SENMARKET_DATA_DIR", "data"))

def raw_dir(run_date: str) -> Path:
    return DATA_DIR / "raw" / f"date={run_date}"

def processed_dir(run_date: str) -> Path:
    return DATA_DIR / "processed" / f"date={run_date}"

def rejected_dir(run_date: str) -> Path:
    return DATA_DIR / "rejected" / f"date={run_date}"

def ensure_dirs(run_date: str) -> None:
    for d in [raw_dir(run_date), processed_dir(run_date), rejected_dir(run_date)]:
        d.mkdir(parents=True, exist_ok=True)