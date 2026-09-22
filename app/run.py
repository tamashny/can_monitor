import sys
from pathlib import Path

# Make the project root importable regardless of how this file is invoked
# (direct script execution, `python -m`, or NiceGUI's reload subprocess,
# which each populate sys.path differently).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.app import main

if __name__ in {"__main__", "__mp_main__"}:
    main()
