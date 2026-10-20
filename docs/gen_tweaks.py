"""
Regenerate docs/TWEAKS.md from the real step tables.

    python docs/gen_tweaks.py

The doc is generated, never hand-edited, so it cannot drift away from what
the app actually does.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# core.engine imports winreg at module level; stub it so this runs anywhere.
if sys.platform != "win32":
    w = types.ModuleType("winreg")
    names = [
        "HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER", "HKEY_CLASSES_ROOT",
        "HKEY_USERS", "REG_DWORD", "REG_QWORD", "REG_SZ", "REG_EXPAND_SZ",
        "REG_MULTI_SZ", "REG_BINARY", "KEY_READ", "KEY_WRITE",
        "KEY_WOW64_64KEY",
    ]
    for i, n in enumerate(names):
        setattr(w, n, i)
    sys.modules["winreg"] = w

from core.profiles import (  # noqa: E402
    PROFILES,
    PULSE_STEPS,
    RISK_NOTICE,
    ULTIMATE_STEPS,
)


def build() -> str:
    out: list[str] = ["# Tweak reference", ""]
    out += [
        "สร้างจากตาราง step ในโค้ดจริง (`core/profiles.py`) ไม่ใช่เขียนมือ",
        "ถ้าโค้ดเปลี่ยน ให้ regenerate ด้วย `python docs/gen_tweaks.py`",
        "",
        f"ULTIMATE V2 รัน {len(ULTIMATE_STEPS)} step · "
        f"PULSE V2 รัน {len(PULSE_STEPS)} step "
        "และเป็น superset ของ ULTIMATE แบบตรงตัว",
        "",
        "## Steps",
        "",
        "| # | Step | ULTIMATE | PULSE |",
        "|---|------|:--------:|:-----:|",
    ]
    ult = {label for label, _ in ULTIMATE_STEPS}
    for i, (label, _) in enumerate(PULSE_STEPS, 1):
        out.append(f"| {i:02} | {label} | {'●' if label in ult else '—'} | ● |")

    out += ["", "## What each step touches", ""]
    for label, fn in PULSE_STEPS:
        doc = (fn.__doc__ or "").strip().splitlines()
        out.append(f"**{label}** — `{fn.__name__}()`")
        if doc:
            out.append(f"  \n{doc[0].strip()}")
        out.append("")

    out += ["## Disclosed risks", ""]
    for key in ("ULTIMATE", "PULSE"):
        out += [f"### {PROFILES[key]['name']}", ""]
        for title, why in RISK_NOTICE[key]:
            out.append(f"- **{title}** — {why}")
        out.append("")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    target = ROOT / "docs" / "TWEAKS.md"
    target.write_text(build(), encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)}")
