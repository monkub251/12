"""
GLOBAL RESET must put the machine back exactly as it was.

If any of these fail, do not ship — the undo button is the only thing
standing between a user and a hand-repaired registry.
"""

from __future__ import annotations

import copy

from tests import fakereg
from tests.conftest import WINREG as W

QOS_KEY = "SOFTWARE\\Policies\\Microsoft\\Windows\\QoS\\BANNARAKX-FiveM"


def _ctx(engine):
    from core.backup import Backup

    b = Backup("TEST")
    return b, engine.Ctx(backup=b, log=lambda m, lv="info": None)


def test_round_trip_restores_every_shape(engine):
    """Overwrite, added value, and created key all unwind."""
    fakereg.REG[(0, "SYSTEM\\Existing")] = {
        "Keep": (W.REG_DWORD, 1), "Target": (W.REG_DWORD, 7)}
    fakereg.REG[(1, "Software\\HasKeyNoVal")] = {"Other": (W.REG_SZ, "x")}
    before = copy.deepcopy(fakereg.REG)

    b, ctx = _ctx(engine)
    ctx.reg("HKLM\\SYSTEM\\Existing", "Target", 42, "dword")      # overwrite
    ctx.reg("HKCU\\Software\\HasKeyNoVal", "NewVal", "hi", "sz")  # new value
    ctx.reg("HKLM\\SYSTEM\\Fresh", "Made", 1, "dword")            # new key
    ctx.reg("HKLM\\SYSTEM\\Existing", "Keep", 99, "dword")        # overwrite

    assert ctx.failed == 0 and ctx.applied == 4
    assert fakereg.REG[(0, "SYSTEM\\Existing")]["Target"][1] == 42
    assert (0, "SYSTEM\\Fresh") in fakereg.REG

    stats = engine.global_reset(b.save(), lambda m, lv="info": None)

    assert stats["fail"] == 0
    assert fakereg.REG == before


def test_many_values_in_one_new_key_unwind_cleanly(engine):
    """The QoS block writes 11 values into one new key.

    Restoring forward would delete the key on the first entry and strand
    the other ten. Restore runs newest-first for exactly this reason.
    """
    fakereg.REG[(0, "SOFTWARE\\Keep")] = {"Untouched": (W.REG_SZ, "keep")}
    before = copy.deepcopy(fakereg.REG)

    b, ctx = _ctx(engine)
    for name, val in [
        ("Version", "1.0"), ("Application Name", "FiveM.exe"),
        ("Protocol", "UDP"), ("Local Port", "*"), ("Local IP", "*"),
        ("Local IP Prefix Length", "*"), ("Remote Port", "*"),
        ("Remote IP", "*"), ("Remote IP Prefix Length", "*"),
        ("DSCP Value", "46"), ("Throttle Rate", "-1"),
    ]:
        ctx.reg(f"HKLM\\{QOS_KEY}", name, val, "sz")

    assert len(fakereg.REG[(0, QOS_KEY)]) == 11

    stats = engine.global_reset(b.save(), lambda m, lv="info": None)

    assert stats["fail"] == 0
    assert (0, QOS_KEY) not in fakereg.REG
    assert fakereg.REG[(0, "SOFTWARE\\Keep")] == before[(0, "SOFTWARE\\Keep")]


def test_reset_is_idempotent(engine):
    """Running the undo twice must not error or damage anything."""
    fakereg.REG[(0, "SYSTEM\\Existing")] = {"Target": (W.REG_DWORD, 7)}
    before = copy.deepcopy(fakereg.REG)

    b, ctx = _ctx(engine)
    ctx.reg("HKLM\\SYSTEM\\Existing", "Target", 42, "dword")
    ctx.reg("HKLM\\SYSTEM\\Fresh2", "Made", 1, "dword")
    snap = b.save()

    engine.global_reset(snap, lambda m, lv="info": None)
    engine.global_reset(snap, lambda m, lv="info": None)

    assert fakereg.REG == before


def test_snapshot_records_old_value_before_writing(engine):
    from core.backup import Backup

    fakereg.REG[(0, "SYSTEM\\X")] = {"V": (W.REG_DWORD, 5)}
    b, ctx = _ctx(engine)
    ctx.reg("HKLM\\SYSTEM\\X", "V", 123, "dword")

    entry = b.data["registry"][0]
    assert entry["old"] == 5
    assert entry["had_value"] is True
    assert entry["key_existed"] is True

    loaded = Backup.load(b.save())
    assert loaded["registry"][0]["old"] == 5


def test_newest_snapshot_is_the_one_restored(engine, isolated_programdata):
    from core.backup import Backup

    b1, ctx1 = _ctx(engine)
    ctx1.reg("HKLM\\SYSTEM\\A", "V", 1, "dword")
    b1.save()

    b2, ctx2 = _ctx(engine)
    ctx2.reg("HKLM\\SYSTEM\\B", "V", 2, "dword")
    newest = b2.save()

    assert Backup.newest() == newest
    assert len(Backup.list_snapshots()) == 2
