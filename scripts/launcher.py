"""Entry file for the packaged app (Nuitka compiles this). Normal runs use `python -m vision_ai`."""

import sys

from vision_ai.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
