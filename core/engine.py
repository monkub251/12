"""
Tweak engine — low level primitives.

Everything that writes goes through here so that (a) the old value is
captured into the Backup first, and (b) failures are reported instead of
silently swallowed.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import winreg
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .backup import Backup

# ---------------------------------------------------------------------------
# elevation
# ---------------------------------------------------------------------------


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """Returns True if an elevated instance was spawned (caller should exit)."""
    if is_admin():
        return False
    args = " ".join(f'"{a}"' for a in sys.argv[1:])
    if getattr(sys, "frozen", False):
        # onefile build: sys.executable IS the app, so argv[0] must NOT be
        # repeated or it arrives as a bogus first argument.
        target, params = sys.executable, args
    else:
        target, params = sys.executable, f'"{sys.argv[0]}" {args}'.strip()
    rc = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", target, params or None, None, 1
    )
    return rc > 32


# ---------------------------------------------------------------------------
# shell helpers
# ---------------------------------------------------------------------------

NOWINDOW = 0x08000000  # CREATE_NO_WINDOW


def run(args, timeout=60) -> tuple[int, str]:
    """Run a command list, return (returncode, combined output)."""
    try:
        p = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=NOWINDOW,
            shell=False,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def ps(script: str, timeout=120) -> tuple[int, str]:
    """Run a PowerShell snippet."""
    return run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# registry
# ---------------------------------------------------------------------------

HIVES = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKU": winreg.HKEY_USERS,
}

TYPES = {
    "dword": winreg.REG_DWORD,
    "qword": winreg.REG_QWORD,
    "sz": winreg.REG_SZ,
    "expand_sz": winreg.REG_EXPAND_SZ,
    "multi_sz": winreg.REG_MULTI_SZ,
    "binary": winreg.REG_BINARY,
}

ACCESS = winreg.KEY_READ | winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY


# ---------------------------------------------------------------------------
# context passed to every step
# ---------------------------------------------------------------------------


@dataclass
class Ctx:
    backup: Backup
    log: Callable[[str, str], None]
    applied: int = 0
    failed: int = 0
    skipped: int = 0
    fivem_path: Path | None = None
    notes: list = field(default_factory=list)

    # -- registry ----------------------------------------------------------
    def reg(self, path: str, name: str, value, vtype="dword", note=""):
        """path is like 'HKLM\\SOFTWARE\\Foo\\Bar'."""
        hive_name, subkey = path.split("\\", 1)
        hive = HIVES[hive_name]
        rt = TYPES[vtype]

        key_existed = True
        old = None
        had_value = False

        try:
            try:
                k = winreg.OpenKey(hive, subkey, 0, ACCESS)
            except FileNotFoundError:
                key_existed = False
                k = winreg.CreateKeyEx(hive, subkey, 0, ACCESS)

            if key_existed:
                try:
                    old, _ = winreg.QueryValueEx(k, name)
                    had_value = True
                except FileNotFoundError:
                    pass

            self.backup.reg(hive_name, subkey, name, vtype, old, had_value, key_existed)
            winreg.SetValueEx(k, name, 0, rt, value)
            winreg.CloseKey(k)

            self.applied += 1
            tail = f"  ({note})" if note else ""
            self.log(f"reg  {subkey.split(chr(92))[-1]}\\{name} = {value}{tail}", "ok")
        except Exception as e:  # noqa: BLE001
            self.failed += 1
            self.log(f"reg  FAILED {path}\\{name} :: {e}", "fail")

    # -- services ----------------------------------------------------------
    def service(self, name: str, start="disabled", stop=True, note=""):
        rc, out = run(["sc", "query", name])
        if rc != 0:
            self.skipped += 1
            self.log(f"svc  {name} not present", "skip")
            return

        was_running = "RUNNING" in out
        rc, qout = run(["sc", "qc", name])
        old_start = "demand"
        for line in qout.splitlines():
            if "START_TYPE" in line:
                low = line.lower()
                if "auto" in low:
                    old_start = "auto"
                elif "disabled" in low:
                    old_start = "disabled"
                elif "demand" in low:
                    old_start = "demand"
                break
        self.backup.service(name, old_start, was_running)

        if stop and was_running:
            run(["sc", "stop", name], timeout=30)

        rc, out = run(["sc", "config", name, f"start={start}"])
        if rc == 0:
            self.applied += 1
            tail = f"  ({note})" if note else ""
            self.log(f"svc  {name} -> {start}{tail}", "ok")
        else:
            # protected service: fall back to the Start value
            smap = {"disabled": 4, "demand": 3, "auto": 2}
            self.reg(
                f"HKLM\\SYSTEM\\CurrentControlSet\\Services\\{name}",
                "Start",
                smap.get(start, 3),
                "dword",
                f"svc {name} fallback",
            )

    # -- scheduled tasks ---------------------------------------------------
    def task_off(self, path: str):
        rc, _ = run(["schtasks", "/Change", "/TN", path, "/Disable"])
        if rc == 0:
            self.applied += 1
            self.log(f"task disabled: {path.split(chr(92))[-1]}", "ok")
        else:
            self.skipped += 1

    # -- powercfg ----------------------------------------------------------
    def powercfg(self, *args):
        rc, out = run(["powercfg", *args])
        return rc, out

    def ok(self, msg):
        self.applied += 1
        self.log(msg, "ok")

    def info(self, msg):
        self.log(msg, "info")

    def warn(self, msg):
        self.log(msg, "warn")


# ---------------------------------------------------------------------------
# FiveM discovery
# ---------------------------------------------------------------------------


def find_fivem() -> Path | None:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "FiveM",
        Path(os.environ.get("PROGRAMFILES", "")) / "FiveM",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "FiveM",
    ]
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:  # noqa: BLE001
            continue
    return None


def dir_size(p: Path) -> int:
    total = 0
    try:
        for f in p.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    except Exception:  # noqa: BLE001
        pass
    return total


def wipe_dir(p: Path, keep: set[str] | None = None) -> int:
    """Delete contents of p (not p itself). Returns bytes freed."""
    keep = keep or set()
    freed = 0
    if not p.exists():
        return 0
    for child in list(p.iterdir()):
        if child.name in keep:
            continue
        sz = dir_size(child) if child.is_dir() else (
            child.stat().st_size if child.exists() else 0
        )
        try:
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
            freed += sz
        except Exception:  # noqa: BLE001
            pass
    return freed


# ---------------------------------------------------------------------------
# GLOBAL RESET
# ---------------------------------------------------------------------------


def global_reset(snapshot_path, log: Callable[[str, str], None]) -> dict:
    data = Backup.load(snapshot_path)
    stats = {"ok": 0, "fail": 0}

    log(f"snapshot: {Path(snapshot_path).name}", "head")

    # Registry, newest write first. Undo order matters: several values often
    # land in one freshly created key, and the entry that removes that key is
    # the FIRST one recorded. Walking forward would delete the key out from
    # under the entries that still have values to remove.
    for r in reversed(data.get("registry", [])):
        try:
            hive = HIVES[r["hive"]]
            if r["had_value"]:
                k = winreg.OpenKey(hive, r["subkey"], 0, ACCESS)
                winreg.SetValueEx(k, r["name"], 0, TYPES[r["type"]], r["old"])
                winreg.CloseKey(k)
                log(f"reg  restored {r['name']} = {r['old']}", "ok")
            elif r["key_existed"]:
                k = winreg.OpenKey(hive, r["subkey"], 0, ACCESS)
                try:
                    winreg.DeleteValue(k, r["name"])
                except FileNotFoundError:
                    pass
                winreg.CloseKey(k)
                log(f"reg  removed {r['name']}", "ok")
            else:
                try:
                    winreg.DeleteKey(hive, r["subkey"])
                    log(f"reg  removed key {r['subkey']}", "ok")
                except OSError:
                    pass
            stats["ok"] += 1
        except Exception as e:  # noqa: BLE001
            stats["fail"] += 1
            log(f"reg  restore failed {r['subkey']}\\{r['name']} :: {e}", "fail")

    # services ---------------------------------------------------------------
    for s in data.get("services", []):
        rc, _ = run(["sc", "config", s["name"], f"start={s['old_start']}"])
        if rc == 0:
            if s["was_running"]:
                run(["sc", "start", s["name"]], timeout=30)
            log(f"svc  restored {s['name']} -> {s['old_start']}", "ok")
            stats["ok"] += 1
        else:
            stats["fail"] += 1
            log(f"svc  restore failed {s['name']}", "fail")

    # power ------------------------------------------------------------------
    old_scheme = data.get("power", {}).get("old_scheme")
    if old_scheme:
        run(["powercfg", "/setactive", old_scheme])
        log(f"power restored scheme {old_scheme}", "ok")
        stats["ok"] += 1

    # netsh ------------------------------------------------------------------
    at = data.get("netsh", {}).get("autotuning")
    if at:
        run(["netsh", "int", "tcp", "set", "global", f"autotuninglevel={at}"])
        log(f"tcp  autotuning restored -> {at}", "ok")
        stats["ok"] += 1

    # nic --------------------------------------------------------------------
    for n in data.get("nic", []):
        rc, _ = ps(
            f'Set-NetAdapterAdvancedProperty -Name "{n["adapter"]}" '
            f'-DisplayName "{n["property"]}" -DisplayValue "{n["old"]}" '
            f"-NoRestart -ErrorAction SilentlyContinue"
        )
        if rc == 0:
            log(f"nic  restored {n['property']}", "ok")
            stats["ok"] += 1

    # misc -------------------------------------------------------------------
    if data.get("mmagent", {}).get("memory_compression"):
        ps("Enable-MMAgent -mc -ErrorAction SilentlyContinue")
        log("memory compression re-enabled", "ok")
        stats["ok"] += 1

    la = data.get("fsutil", {}).get("last_access")
    if la is not None:
        run(["fsutil", "behavior", "set", "disablelastaccess", str(la)])
        log(f"fsutil last-access restored -> {la}", "ok")
        stats["ok"] += 1

    # DNS back to DHCP -------------------------------------------------------
    ps(
        "Get-NetAdapter | Where-Object Status -eq 'Up' | "
        "Set-DnsClientServerAddress -ResetServerAddresses "
        "-ErrorAction SilentlyContinue"
    )
    run(["ipconfig", "/flushdns"])
    log("dns  reset to DHCP", "ok")

    log("GLOBAL RESET complete — reboot to finish", "head")
    return stats
