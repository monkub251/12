"""
Backup store.

Every mutation the engine performs is recorded here BEFORE it is written.
GLOBAL RESET replays the newest snapshot in reverse.

Snapshot layout (JSON):
{
  "meta":     {created, profile, computer, os},
  "registry": [{hive, subkey, name, type, old, had_value, key_existed}],
  "services": [{name, old_start, was_running}],
  "power":    {old_scheme},
  "netsh":    {autotuning, ...},
  "nic":      [{adapter, property, old}],
  "fsutil":   {last_access},
  "mmagent":  {memory_compression}
}
"""

from __future__ import annotations

import json
import os
import platform
import socket
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "BANNARAKX"
BACKUP_DIR = ROOT / "backups"
LOG_DIR = ROOT / "logs"


class Backup:
    def __init__(self, profile: str):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Second-resolution stamps collide when two runs start inside the same
        # second, and the loser is overwritten — taking the only record of the
        # original values with it. Microseconds, fixed width, so the filename
        # sorts chronologically as plain text. A variable-width collision
        # suffix would not: "…-966-1.json" sorts BELOW "…-966.json".
        while True:
            now = datetime.now()
            self.stamp = (now.strftime("%Y%m%d-%H%M%S-")
                          + f"{now.microsecond:06d}")
            self.path = BACKUP_DIR / f"backup-{self.stamp}.json"
            if not self.path.exists():
                break
            time.sleep(0.001)
        self.data = {
            "meta": {
                "created": datetime.now().isoformat(timespec="seconds"),
                "profile": profile,
                "computer": socket.gethostname(),
                "os": platform.platform(),
            },
            "registry": [],
            "services": [],
            "power": {},
            "netsh": {},
            "nic": [],
            "fsutil": {},
            "mmagent": {},
        }

    # -- recorders ---------------------------------------------------------
    def reg(self, hive, subkey, name, vtype, old, had_value, key_existed):
        self.data["registry"].append(
            {
                "hive": hive,
                "subkey": subkey,
                "name": name,
                "type": vtype,
                "old": old,
                "had_value": had_value,
                "key_existed": key_existed,
            }
        )

    def service(self, name, old_start, was_running):
        self.data["services"].append(
            {"name": name, "old_start": old_start, "was_running": was_running}
        )

    def nic(self, adapter, prop, old):
        self.data["nic"].append({"adapter": adapter, "property": prop, "old": old})

    def set(self, section, key, value):
        self.data[section][key] = value

    # -- io ----------------------------------------------------------------
    def save(self):
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return self.path

    @staticmethod
    def list_snapshots():
        """Newest first. Sorted by name, not mtime: names carry the stamp and
        two files written in the same millisecond can share an mtime."""
        if not BACKUP_DIR.exists():
            return []
        return sorted(BACKUP_DIR.glob("backup-*.json"),
                      key=lambda p: p.name, reverse=True)

    @staticmethod
    def newest():
        snaps = Backup.list_snapshots()
        return snaps[0] if snaps else None

    @staticmethod
    def load(path):
        return json.loads(Path(path).read_text(encoding="utf-8"))
