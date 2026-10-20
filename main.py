"""
BANNARAKX — FIVE M · FPS OPTIMIZER
Windows desktop front end for the tweak engine in core/.

    python main.py          run from source (asks for Administrator)
    build.bat               produce dist/BANNARAKX.exe
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core import sysinfo
from core.backup import BACKUP_DIR, LOG_DIR, Backup
from core.engine import Ctx, global_reset, is_admin, relaunch_as_admin
from core.profiles import PROFILES, RISK_NOTICE
from ui.theme import (
    ACCENT,
    BAD,
    DIM,
    FAINT,
    LINE,
    OK,
    PANEL,
    QSS,
    TEXT,
    WARN,
)
from ui.widgets import (
    ActionButton,
    DotField,
    Mark,
    ProfileTile,
    ScanBar,
    StatCell,
    StatusDot,
)

APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ASSETS = APP_DIR / "assets"
VERSION = "v2.0"
MAX_STEPS = max(len(p["steps"]) for p in PROFILES.values())


# ===========================================================================
# workers
# ===========================================================================


class RunWorker(QObject):
    line = Signal(str, str)
    progress = Signal(int, int, str)
    done = Signal(dict)

    def __init__(self, mode: str, key: str = ""):
        super().__init__()
        self.mode, self.key = mode, key

    def run(self):
        self._optimize() if self.mode == "optimize" else self._reset()

    def _optimize(self):
        profile = PROFILES[self.key]
        backup = Backup(profile["name"])
        logfile = LOG_DIR / f"run-{backup.stamp}.log"

        def log(msg, level="info"):
            self.line.emit(msg, level)
            try:
                with logfile.open("a", encoding="utf-8") as fh:
                    fh.write(f"[{level}] {msg}\n")
            except OSError:
                pass

        ctx = Ctx(backup=backup, log=log)
        log(f"{profile['name']} — {len(profile['steps'])} steps", "head")

        total = len(profile["steps"])
        for i, (label, fn) in enumerate(profile["steps"], 1):
            self.progress.emit(i, total, label)
            log(f"[{i:02}/{total}] {label}", "head")
            try:
                fn(ctx)
            except Exception as e:  # noqa: BLE001
                ctx.failed += 1
                log(f"step failed :: {e}", "fail")

        path = backup.save()
        log(f"snapshot saved: {path}", "ok")
        self.done.emit({
            "applied": ctx.applied, "failed": ctx.failed,
            "skipped": ctx.skipped, "mode": "optimize",
        })

    def _reset(self):
        snap = Backup.newest()
        if not snap:
            self.line.emit("no snapshot found — nothing to reset", "fail")
            self.done.emit({"applied": 0, "failed": 0, "skipped": 0, "mode": "reset"})
            return
        self.progress.emit(1, 1, "GLOBAL RESET")
        stats = global_reset(snap, lambda m, lv="info": self.line.emit(m, lv))
        self.done.emit({
            "applied": stats["ok"], "failed": stats["fail"],
            "skipped": 0, "mode": "reset",
        })


class InfoWorker(QObject):
    ready = Signal(object)

    def run(self):
        try:
            self.ready.emit(sysinfo.collect())
        except Exception:  # noqa: BLE001
            self.ready.emit(sysinfo.SysInfo())


# ===========================================================================
# consent dialog
# ===========================================================================


def _wrapping(label: QLabel, width: int) -> QLabel:
    """A wrapped QLabel only reports its true height when the size policy
    asks for heightForWidth. Without this, two-line text gets a one-line
    slot and the next widget draws straight over it."""
    label.setWordWrap(True)
    label.setFixedWidth(width)
    sp = label.sizePolicy()
    sp.setHeightForWidth(True)
    sp.setVerticalPolicy(QSizePolicy.Minimum)
    label.setSizePolicy(sp)
    label.setMinimumHeight(label.heightForWidth(width))
    return label


class RiskDialog(QDialog):
    WIDTH = 600
    INNER = 600 - 38 * 2

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedWidth(self.WIDTH)
        self.setStyleSheet(f"QDialog {{ background:{PANEL}; border:1px solid {LINE}; }}")

        v = QVBoxLayout(self)
        v.setContentsMargins(38, 32, 38, 28)
        v.setSpacing(0)

        eyebrow = QLabel("CONSENT REQUIRED")
        eyebrow.setProperty("role", "eyebrow")
        eyebrow.setStyleSheet(f"color:{BAD}; letter-spacing:3px; font-size:9px;")
        v.addWidget(eyebrow)
        v.addSpacing(8)

        t = QLabel(f"{PROFILES[key]['name']} weakens this machine")
        tf = QFont("Rajdhani", 19)
        tf.setWeight(QFont.Bold)
        tf.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        t.setFont(tf)
        v.addWidget(t)
        v.addSpacing(10)

        sub = QLabel(
            "ทุกข้อด้านล่างลดความปลอดภัยของเครื่องจริง และย้อนกลับได้ทั้งหมด"
            "ด้วย GLOBAL RESET — อ่านให้จบก่อนกด"
        )
        sub.setProperty("role", "body")
        sub.setStyleSheet(f"color:{DIM}; font-size:13px;")
        v.addWidget(_wrapping(sub, self.INNER))
        v.addSpacing(18)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background:{LINE};")
        v.addWidget(rule)
        v.addSpacing(16)

        for title, why in RISK_NOTICE[key]:
            row = QLabel(title)
            rf = QFont("Rajdhani", 11)
            rf.setWeight(QFont.DemiBold)
            row.setFont(rf)
            row.setStyleSheet(f"color:{TEXT};")
            v.addWidget(_wrapping(row, self.INNER))
            v.addSpacing(3)

            d = QLabel(why)
            d.setStyleSheet(f"color:{FAINT}; font-size:11px;")
            v.addWidget(_wrapping(d, self.INNER))
            v.addSpacing(14)

        v.addSpacing(4)
        row = QHBoxLayout()
        row.setSpacing(12)
        cancel = ActionButton("CANCEL", primary=False)
        cancel.setFixedWidth(160)
        go = ActionButton("I UNDERSTAND — RUN", primary=True)
        cancel.clicked.connect(self.reject)
        go.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(go, 1)
        v.addLayout(row)
        self.adjustSize()


# ===========================================================================
# main window
# ===========================================================================


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setObjectName("root")
        self.resize(1180, 784)
        self.setMinimumSize(1060, 720)

        self.current = "ULTIMATE"
        self.busy = False
        self._drag = None
        self.run_thread = self.run_worker = None
        self.info_thread = self.info_worker = None
        self.counters = {"applied": 0, "failed": 0, "skipped": 0}

        self.bg = DotField(self)
        self.bg.lower()

        shell = QHBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_rail())

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self._build_header())
        right.addWidget(self._rule())
        self.scan = ScanBar()
        right.addWidget(self.scan)
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        right.addWidget(self._rule())
        right.addWidget(self._build_footer())
        shell.addLayout(right, 1)

        for page in (self._build_home(), self._build_log(), self._build_about()):
            self.stack.addWidget(page)

        self._select("ULTIMATE")
        self._nav_to(0)
        self._load_sysinfo()

    # -- chrome --------------------------------------------------------
    def _rule(self):
        f = QFrame()
        f.setFixedHeight(1)
        f.setStyleSheet(f"background:{LINE};")
        return f

    def _build_rail(self):
        rail = QWidget()
        rail.setObjectName("rail")
        rail.setFixedWidth(78)
        v = QVBoxLayout(rail)
        v.setContentsMargins(0, 22, 0, 18)
        v.setSpacing(0)

        logo_path = ASSETS / "logo.png"
        if logo_path.exists():
            lab = QLabel()
            lab.setPixmap(QPixmap(str(logo_path)).scaled(
                36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            lab.setAlignment(Qt.AlignCenter)
            v.addWidget(lab)
        else:
            holder = QHBoxLayout()
            holder.addStretch(1)
            holder.addWidget(Mark(34))
            holder.addStretch(1)
            v.addLayout(holder)

        v.addSpacing(30)
        self.navs = []
        for i, label in enumerate(("HOME", "LOG", "ABOUT")):
            b = QPushButton(label)
            b.setProperty("role", "rail")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, n=i: self._nav_to(n))
            v.addWidget(b)
            self.navs.append(b)

        v.addStretch(1)
        ver = QLabel(VERSION)
        ver.setAlignment(Qt.AlignCenter)
        ver.setProperty("role", "mono")
        v.addWidget(ver)
        return rail

    def _build_header(self):
        bar = QWidget()
        bar.setFixedHeight(88)
        h = QHBoxLayout(bar)
        h.setContentsMargins(30, 0, 16, 0)
        h.setSpacing(0)

        holder = QWidget()
        holder.setFixedWidth(206)
        name = QVBoxLayout(holder)
        name.setContentsMargins(0, 0, 0, 0)
        name.setSpacing(4)
        w = QLabel("BANNARAKX")
        w.setProperty("role", "wordmark")
        s = QLabel("FIVE M · FPS OPTIMIZER")
        s.setProperty("role", "tagline")
        name.addWidget(w)
        name.addWidget(s)
        h.addWidget(holder, 0, Qt.AlignVCenter)
        h.addSpacing(22)

        self.cells = {}
        for keyname, label in (
            ("cpu", "PROCESSOR"), ("gpu", "GRAPHICS"),
            ("ram", "MEMORY"), ("display", "DISPLAY"),
        ):
            cell = StatCell(label)
            self.cells[keyname] = cell
            h.addWidget(cell, 2 if keyname in ("cpu", "gpu") else 1, Qt.AlignVCenter)
            h.addSpacing(18)

        h.addStretch(0)
        for glyph, role, fn in (
            ("–", "win", self.showMinimized),
            ("□", "win", self._toggle_max),
            ("✕", "close", self.close),
        ):
            b = QPushButton(glyph)
            b.setProperty("role", role)
            b.setFixedSize(32, 32)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            h.addWidget(b, 0, Qt.AlignTop)
        return bar

    def _toggle_max(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    # -- home ----------------------------------------------------------
    def _build_home(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(30, 26, 30, 24)
        v.setSpacing(0)

        top = QHBoxLayout()
        eyebrow = QLabel("SELECT PROFILE")
        eyebrow.setProperty("role", "eyebrow")
        top.addWidget(eyebrow)
        top.addStretch(1)
        self.snap_label = QLabel()
        self.snap_label.setProperty("role", "mono")
        top.addWidget(self.snap_label)
        v.addLayout(top)
        v.addSpacing(16)

        tiles = QHBoxLayout()
        tiles.setSpacing(18)
        self.tiles = {}
        for key in ("ULTIMATE", "PULSE"):
            tile = ProfileTile(key, PROFILES[key], MAX_STEPS)
            tile.clicked.connect(self._select)
            tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tile.setFixedHeight(404)
            tiles.addWidget(tile, 1)
            self.tiles[key] = tile
        v.addLayout(tiles, 0)

        v.addSpacing(18)
        safety = QLabel(
            "ทุกค่าถูกบันทึกลง snapshot ก่อนเขียนเสมอ  ·  GLOBAL RESET "
            "อ่าน snapshot ล่าสุดแล้วคืนค่าทีละตัว  ·  รีบูตหลังรันทุกครั้ง")
        safety.setProperty("role", "note")
        safety.setWordWrap(True)
        v.addWidget(safety)

        v.addStretch(1)
        self.advice = QLabel()
        self.advice.setWordWrap(True)
        self.advice.setProperty("role", "note")
        self.advice.setVisible(False)
        v.addWidget(self.advice)
        v.addSpacing(12)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.btn_go = ActionButton("OPTIMIZE", "", primary=True)
        self.btn_go.clicked.connect(self._on_optimize)
        actions.addWidget(self.btn_go, 1)

        self.btn_reset = ActionButton(
            "GLOBAL RESET", "คืนค่าทุกอย่างที่แอปเคยปรับ", primary=False)
        self.btn_reset.setFixedWidth(300)
        self.btn_reset.setFixedHeight(58)
        self.btn_reset.clicked.connect(self._on_reset)
        actions.addWidget(self.btn_reset)
        v.addLayout(actions)
        return page

    # -- log -----------------------------------------------------------
    def _build_log(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(30, 26, 30, 24)
        v.setSpacing(0)

        head = QHBoxLayout()
        t = QLabel("LOG")
        t.setProperty("role", "pagetitle")
        head.addWidget(t)
        head.addStretch(1)

        self.count_cells = {}
        for keyname, label in (
            ("applied", "APPLIED"), ("failed", "FAILED"), ("skipped", "SKIPPED"),
        ):
            cell = StatCell(label)
            cell.setFixedWidth(104)
            cell.set("0")
            self.count_cells[keyname] = cell
            head.addWidget(cell, 0, Qt.AlignBottom)
            head.addSpacing(10)

        clear = QPushButton("CLEAR")
        clear.setProperty("role", "rail")
        clear.setFixedWidth(72)
        clear.setCursor(Qt.PointingHandCursor)
        clear.clicked.connect(self._clear_log)
        head.addWidget(clear, 0, Qt.AlignBottom)
        v.addLayout(head)
        v.addSpacing(18)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(8000)
        self.console.setPlaceholderText("ยังไม่มีการรัน — กลับไปหน้า HOME แล้วกด OPTIMIZE")
        v.addWidget(self.console, 1)
        v.addSpacing(10)

        p = QLabel(f"log  {LOG_DIR}\nsnap {BACKUP_DIR}")
        p.setProperty("role", "mono")
        v.addWidget(p)
        return page

    def _clear_log(self):
        self.console.clear()
        self.counters = {k: 0 for k in self.counters}
        self._refresh_counters()

    def _refresh_counters(self):
        for k, cell in self.count_cells.items():
            cell.set(str(self.counters[k]), flagged=(k == "failed"
                                                     and self.counters[k] > 0))

    # -- about ---------------------------------------------------------
    def _build_about(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(30, 26, 30, 24)
        v.setSpacing(0)

        t = QLabel("ABOUT")
        t.setProperty("role", "pagetitle")
        v.addWidget(t)
        v.addSpacing(20)

        blocks = [
            ("HOW THE UNDO WORKS",
             "ทุกค่าที่แอปเขียน จะบันทึกค่าเดิมลง snapshot JSON ก่อนเขียนเสมอ\n"
             "GLOBAL RESET อ่าน snapshot ล่าสุดแล้วคืนค่าทีละตัว ย้อนลำดับ:\n"
             "ค่าเดิมมี → เขียนกลับ · ค่าเดิมไม่มีแต่ key มี → ลบเฉพาะค่านั้น · "
             "key เพิ่งถูกสร้าง → ลบทั้ง key\n"
             "คืน service, power scheme, TCP autotuning, NIC, memory compression "
             "และ DNS กลับเป็น DHCP ด้วย"),
            ("WHAT THIS APP CANNOT DO — เรียงตามผลจริง",
             "1  เปิด XMP / EXPO ใน BIOS — ได้ FPS มากกว่าทุกอย่างในแอปรวมกัน\n"
             "2  ใช้สาย LAN — jitter ของ Wi-Fi กินทุก network tweak ในนี้\n"
             "3  FPS cap = refresh rate ลบ 3 + Low Latency Mode Ultra\n"
             "4  G-Sync/FreeSync เปิด · VSync ไดรเวอร์เปิด · VSync ในเกมปิด\n"
             "5  Population Density + Distance Scaling เหลือ 0–30%"),
            ("HONEST NUMBERS",
             "ปิด Spectre/Meltdown บน Zen 3+ หรือ Intel 10th gen ขึ้นไป ได้เกือบศูนย์ "
             "เพราะ CPU แก้ที่ hardware แล้ว\n"
             "ปิด memory compression บนเครื่อง RAM 16GB หรือน้อยกว่า "
             "ทำให้กระตุกหนักกว่าเดิม ไม่ใช่ดีขึ้น"),
        ]
        for head, body in blocks:
            hl = QLabel(head)
            hl.setProperty("role", "eyebrow")
            v.addWidget(hl)
            v.addSpacing(6)
            bl = QLabel(body)
            bl.setProperty("role", "body")
            bl.setWordWrap(True)
            v.addWidget(bl)
            v.addSpacing(22)

        v.addStretch(1)
        return page

    # -- footer --------------------------------------------------------
    def _build_footer(self):
        bar = QWidget()
        bar.setFixedHeight(42)
        h = QHBoxLayout(bar)
        h.setContentsMargins(30, 0, 30, 0)
        h.setSpacing(10)

        self.dot = StatusDot()
        h.addWidget(self.dot)
        lab = QLabel("STATUS")
        lab.setProperty("role", "eyebrow")
        h.addWidget(lab)
        h.addSpacing(6)
        self.status = QLabel("READY")
        self.status.setStyleSheet(
            f"color:{TEXT}; font-size:10px; letter-spacing:2.5px;")
        h.addWidget(self.status)
        h.addStretch(1)

        self.os_label = QLabel()
        self.os_label.setProperty("role", "mono")
        h.addWidget(self.os_label)
        return bar

    # -- behaviour -----------------------------------------------------
    def resizeEvent(self, e):
        self.bg.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(e)

    def _nav_to(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self.navs):
            b.setProperty("active", "true" if i == idx else "false")
            b.style().unpolish(b)
            b.style().polish(b)

    def _select(self, key):
        if self.busy:
            return
        self.current = key
        for k, tile in self.tiles.items():
            tile.set_selected(k == key)
        d = PROFILES[key]
        self.btn_go.set_text(sub=f"{d['name']} · {len(d['steps'])} steps · "
                                 f"{d['impact'].lower()}")

    def _set_status(self, text, color=FAINT, pulse=False):
        self.status.setText(text)
        self.status.setStyleSheet(
            f"color:{color}; font-size:10px; letter-spacing:2.5px;")
        self.dot.set(color, pulse)

    def _append(self, msg, level):
        colors = {"ok": DIM, "fail": BAD, "warn": WARN,
                  "head": TEXT, "skip": "#3A3C42", "info": FAINT}
        weight = "600" if level == "head" else "400"
        safe = (msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        self.console.appendHtml(
            f'<span style="color:{colors.get(level, DIM)};'
            f'font-weight:{weight}">{safe or "&nbsp;"}</span>')

    # -- system readout --------------------------------------------------
    def _load_sysinfo(self):
        self._refresh_snapshot_label()
        self.info_thread = QThread()
        self.info_worker = InfoWorker()
        self.info_worker.moveToThread(self.info_thread)
        self.info_thread.started.connect(self.info_worker.run)
        self.info_worker.ready.connect(self._on_sysinfo)
        self.info_thread.start()

    def _on_sysinfo(self, s):
        self.cells["cpu"].set(s.cpu, s.cores)
        self.cells["gpu"].set(s.gpu, s.vram)
        self.cells["ram"].set(s.ram, s.disk, flagged=bool(s.warnings))
        self.cells["display"].set(s.display, s.cap or s.power)
        self.os_label.setText(f"{s.os_name}  ·  {s.power}")
        if s.warnings:
            self.advice.setText("⚠  " + "  ".join(s.warnings))
            self.advice.setStyleSheet(f"color:{WARN}; font-size:11px;")
            self.advice.setVisible(True)
        if self.info_thread:
            self.info_thread.quit()
            self.info_thread.wait(2000)

    def _refresh_snapshot_label(self):
        snap = Backup.newest()
        if snap:
            raw = snap.stem.replace("backup-", "")
            d, t = (raw.split("-") + ["", ""])[:2]
            pretty = f"{d[:4]}-{d[4:6]}-{d[6:8]}  {t[:2]}:{t[2:4]}:{t[4:6]}"
            self.snap_label.setText(f"LAST SNAPSHOT  {pretty}")
            self.btn_reset.set_enabled(True)
        else:
            self.snap_label.setText("NO SNAPSHOT YET")
            self.btn_reset.set_enabled(False)

    # -- run -----------------------------------------------------------
    def _on_optimize(self):
        if self.busy:
            return
        if RiskDialog(self.current, self).exec() != QDialog.Accepted:
            self._set_status("CANCELLED", WARN)
            return
        self._start("optimize", self.current)

    def _on_reset(self):
        if self.busy or not Backup.newest():
            return
        self._start("reset")

    def _start(self, mode, key=""):
        self.busy = True
        self.btn_go.set_enabled(False)
        self.btn_reset.set_enabled(False)
        self.counters = {k: 0 for k in self.counters}
        self._refresh_counters()
        self.console.clear()
        self.scan.start()
        self._set_status("RUNNING", ACCENT, pulse=True)
        self._nav_to(1)

        self.run_thread = QThread()
        self.run_worker = RunWorker(mode, key)
        self.run_worker.moveToThread(self.run_thread)
        self.run_thread.started.connect(self.run_worker.run)
        self.run_worker.line.connect(self._append)
        self.run_worker.progress.connect(self._on_progress)
        self.run_worker.done.connect(self._on_done)
        self.run_thread.start()

    def _on_progress(self, i, total, label):
        self.scan.set_progress(i, total)
        self._set_status(f"{i:02}/{total}  {label.upper()}", ACCENT, pulse=True)

    def _on_done(self, stats):
        self.busy = False
        self.scan.stop()
        if self.run_thread:
            self.run_thread.quit()
            self.run_thread.wait(4000)

        self.counters.update({k: stats.get(k, 0) for k in self.counters})
        self._refresh_counters()
        self._refresh_snapshot_label()
        self.btn_go.set_enabled(True)

        ok, fail = stats.get("applied", 0), stats.get("failed", 0)
        verb = "RESET" if stats.get("mode") == "reset" else "OPTIMIZED"
        self._set_status(
            f"{verb} · {ok} APPLIED · {fail} FAILED · REBOOT REQUIRED",
            OK if fail == 0 else WARN)
        self._append("", "info")
        self._append("reboot to finish — power, NIC and kernel changes need it",
                     "head")

    # -- frameless window ------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 88 \
                and e.position().x() > 78:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.LeftButton and not self.isMaximized():
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _e):
        self._drag = None

    def closeEvent(self, e):
        if self.busy:
            e.ignore()
            return
        for th in (self.run_thread, self.info_thread):
            if th and th.isRunning():
                th.quit()
                th.wait(2000)
        e.accept()


# ===========================================================================
def main() -> int:
    if sys.platform != "win32":
        print("BANNARAKX is Windows only.")
        return 1
    if not is_admin() and relaunch_as_admin():
        return 0

    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    ico = ASSETS / "logo.ico"
    if ico.exists():
        app.setWindowIcon(QIcon(str(ico)))

    win = Window()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
