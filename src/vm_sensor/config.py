from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = PROJECT_ROOT / "assets"
MODEL_DIR = ASSET_DIR / "models"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "captures"

WINDOW_TITLE = "VM Sensor - Realtime Segment UI"
WINDOW_SIZE = "1380x860"
REFRESH_INTERVAL_MS = 33
PREVIEW_WIDTH = 620
PREVIEW_HEIGHT = 420
