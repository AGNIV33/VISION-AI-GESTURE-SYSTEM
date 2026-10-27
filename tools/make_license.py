"""Owner-only tool: make license keys.

python tools/make_license.py --init
    Makes your private signing key (kept in %APPDATA%\\VisionAI\\owner_private.key, NEVER
    commit or share it) and writes the matching public key into the app.
python tools/make_license.py --who you@mail.com --plan owner
    Prints a key that unlocks everything for free (for you).
python tools/make_license.py --who buyer@mail.com --plan pro [--expires 2027-12-31]
    Prints a key to give a buyer.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vision_ai.config.calibration import data_dir  # noqa: E402
from vision_ai.licensing import ed25519, license  # noqa: E402

PUBLIC_FILE = ROOT / "src" / "vision_ai" / "licensing" / "public_key.py"


def private_path() -> Path:
    return data_dir() / "owner_private.key"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--init", action="store_true")
    p.add_argument("--who", default="")
    p.add_argument("--plan", choices=["pro", "owner"], default="pro")
    p.add_argument("--expires", default="", help="YYYY-MM-DD, empty = never")
    a = p.parse_args()

    path = private_path()
    if a.init:
        if path.exists():
            print(f"Private key already exists: {path}\nDelete it only if you want new keys.")
            return 1
        path.parent.mkdir(parents=True, exist_ok=True)
        secret = os.urandom(32)
        path.write_bytes(secret)
        pub = ed25519.public_key(secret).hex()
        PUBLIC_FILE.write_text(
            '"""The public half of the license-signing key (safe to publish)."""\n\n'
            f'PUBLIC_KEY_HEX = "{pub}"\n',
            encoding="utf-8",
        )
        print(f"Private key saved: {path}  (BACK IT UP, never share it)")
        print(f"Public key written to: {PUBLIC_FILE}")
        return 0

    if not path.exists():
        print("No private key yet. Run:  python tools/make_license.py --init")
        return 1
    if not a.who:
        print("Give --who (email or name).")
        return 1
    key = license.make_key(path.read_bytes(), a.plan, a.who, a.expires)
    info = license.check(key)
    print(key)
    print(f"\nChecked: valid={info.valid} plan={info.plan} who={info.who}", file=sys.stderr)
    return 0 if info.valid else 1


if __name__ == "__main__":
    sys.exit(main())
