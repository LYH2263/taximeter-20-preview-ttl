import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DB_FILENAME = "app.db"

# 打表预览令牌有效期（秒），过期后须重新预览才能落表
PREVIEW_TOKEN_TTL_SECONDS = int(os.environ.get("PREVIEW_TOKEN_TTL_SECONDS", "60"))
