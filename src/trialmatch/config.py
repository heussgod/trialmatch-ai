from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BENCHMARK_DIR = DATA_DIR / "benchmarks"

TRIAL_SNAPSHOT_PATH = RAW_DIR / "trials_snapshot.jsonl"
BENCHMARK_PATH = BENCHMARK_DIR / "patient_profiles.json"

DEFAULT_CONDITIONS = [
    "heart failure",
    "type 2 diabetes",
    "parkinson disease",
    "chronic obstructive pulmonary disease",
    "breast cancer",
]

OPEN_STATUSES = {
    "RECRUITING",
    "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING",
}
