"""
In-memory stand-in for the Windows registry.

Lets the restore logic be tested on any OS, including CI runners, without
touching a real machine. Install it BEFORE core.engine is imported.
"""

from __future__ import annotations

import sys
import types

# (hive_int, subkey) -> {value_name: (type, value)}
REG: dict[tuple[int, str], dict] = {}


def install() -> types.ModuleType:
    w = types.ModuleType("winreg")
    w.HKEY_LOCAL_MACHINE = 0
    w.HKEY_CURRENT_USER = 1
    w.HKEY_CLASSES_ROOT = 2
    w.HKEY_USERS = 3
    for i, n in enumerate(
        ["REG_DWORD", "REG_QWORD", "REG_SZ", "REG_EXPAND_SZ",
         "REG_MULTI_SZ", "REG_BINARY"]
    ):
        setattr(w, n, 100 + i)
    w.KEY_READ, w.KEY_WRITE, w.KEY_WOW64_64KEY = 1, 2, 4

    class Handle:
        __slots__ = ("hive", "sub")

        def __init__(self, hive, sub):
            self.hive, self.sub = hive, sub

    def OpenKey(hive, sub, _res=0, _acc=0):
        if (hive, sub) not in REG:
            raise FileNotFoundError(sub)
        return Handle(hive, sub)

    def CreateKeyEx(hive, sub, _res=0, _acc=0):
        REG.setdefault((hive, sub), {})
        return Handle(hive, sub)

    def QueryValueEx(h, name):
        d = REG[(h.hive, h.sub)]
        if name not in d:
            raise FileNotFoundError(name)
        return d[name][1], d[name][0]

    def SetValueEx(h, name, _res, vtype, value):
        REG[(h.hive, h.sub)][name] = (vtype, value)

    def CloseKey(_h):
        pass

    def DeleteValue(h, name):
        d = REG[(h.hive, h.sub)]
        if name not in d:
            raise FileNotFoundError(name)
        del d[name]

    def DeleteKey(hive, sub):
        # real DeleteKey refuses a key that still has SUBkeys
        if (hive, sub) not in REG:
            raise OSError(sub)
        if any(k[0] == hive and k[1].startswith(sub + "\\") for k in REG):
            raise OSError("key has subkeys")
        del REG[(hive, sub)]

    for fn in (OpenKey, CreateKeyEx, QueryValueEx, SetValueEx,
               CloseKey, DeleteValue, DeleteKey):
        setattr(w, fn.__name__, fn)

    sys.modules["winreg"] = w
    return w


def reset():
    REG.clear()
