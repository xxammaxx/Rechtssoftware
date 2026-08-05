"""Start FastAPI test server without seed data.

Usage: python rc017_server.py <data_dir> <port>
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from private_legal_navigator.config import Settings
from private_legal_navigator.app import create_app
import uvicorn

data_dir = Path(sys.argv[1])
port = int(sys.argv[2])

data_dir.mkdir(parents=True, exist_ok=True)
(data_dir / "documents").mkdir(exist_ok=True)
(data_dir / "snapshots").mkdir(exist_ok=True)

settings = Settings(data_dir=data_dir, host="127.0.0.1", port=port)
app = create_app(settings)

config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
server = uvicorn.Server(config)
server.run()
