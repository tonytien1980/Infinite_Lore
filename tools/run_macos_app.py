import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_shell.main import default_config_path, default_vault_root, launch_app


if __name__ == "__main__":
    launch_app(vault_root=default_vault_root(), config_path=default_config_path())
