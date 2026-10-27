"""License keys: signed text that the app checks offline (no server needed).

A key is   VAI1.<base32 text>   holding a small JSON note + an Ed25519 signature.
Only the owner's private key can make a valid key, so nobody can invent one.
Selling online later (Lemon Squeezy, Keygen, ...) only changes HOW keys are delivered:
the provider's webhook can call tools/make_license.py on your server.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import date

from vision_ai.licensing import ed25519
from vision_ai.licensing.public_key import PUBLIC_KEY_HEX

PREFIX = "VAI1."
PAID_PLANS = ("pro", "owner")


@dataclass(frozen=True)
class LicenseInfo:
    valid: bool
    plan: str = "free"  # "free" | "pro" | "owner"
    who: str = ""
    expires: str = ""  # "" = never
    reason: str = ""  # why it is not valid (shown in Settings)

    @property
    def paid(self) -> bool:
        return self.valid and self.plan in PAID_PLANS


FREE = LicenseInfo(valid=False, plan="free")


def _b32(data: bytes) -> str:
    return base64.b32encode(data).decode("ascii").rstrip("=")


def _unb32(text: str) -> bytes:
    text = text.strip().upper()
    return base64.b32decode(text + "=" * (-len(text) % 8))


def make_key(secret: bytes, plan: str, who: str, expires: str = "") -> str:
    note = json.dumps({"p": plan, "w": who, "x": expires}, separators=(",", ":")).encode()
    sig = ed25519.sign(secret, note)
    return PREFIX + _b32(len(note).to_bytes(2, "big") + note + sig)


def check(key: str, today: date | None = None, public_hex: str | None = None) -> LicenseInfo:
    """Check a key. Never raises: a bad key just gives a LicenseInfo with a reason."""
    key = "".join(key.split())  # users paste keys with spaces / line breaks
    if not key:
        return FREE
    pub_hex = PUBLIC_KEY_HEX if public_hex is None else public_hex
    if not pub_hex:
        return LicenseInfo(False, reason="This build has no license key set up yet.")
    if not key.startswith(PREFIX):
        return LicenseInfo(False, reason="This does not look like a Vision AI key.")
    try:
        raw = _unb32(key[len(PREFIX) :])
        n = int.from_bytes(raw[:2], "big")
        note, sig = raw[2 : 2 + n], raw[2 + n :]
        if len(note) != n or len(sig) != 64:
            raise ValueError("wrong length")
        ok = ed25519.verify(bytes.fromhex(pub_hex), note, sig)
        data = json.loads(note)
    except (ValueError, TypeError, KeyError):
        return LicenseInfo(False, reason="The key is damaged. Copy it again completely.")
    if not ok:
        return LicenseInfo(False, reason="The key is not valid.")
    plan, who, exp = str(data.get("p", "")), str(data.get("w", "")), str(data.get("x", ""))
    if plan not in PAID_PLANS:
        return LicenseInfo(False, reason="Unknown plan in the key.")
    if exp:
        try:
            if (today or date.today()) > date.fromisoformat(exp):
                return LicenseInfo(False, plan, who, exp, reason=f"The key expired on {exp}.")
        except ValueError:
            return LicenseInfo(False, reason="The key has a bad date.")
    return LicenseInfo(True, plan, who, exp)
