"""
Read-only machine readout for the header strip.

Everything here is a fact pulled off the live machine — CPU, GPU, RAM,
display, power scheme. Nothing is estimated and nothing is written.
Runs off the UI thread because WMI is slow to wake up.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .engine import ps, run


@dataclass
class SysInfo:
    cpu: str = "—"
    cores: str = ""
    gpu: str = "—"
    vram: str = ""
    ram: str = "—"
    display: str = "—"
    cap: str = ""
    os_name: str = "—"
    power: str = "—"
    disk: str = "—"
    refresh_hz: int = 0
    warnings: list = field(default_factory=list)


def _one(script: str) -> str:
    """First line of output, or "" — a failed probe must never reach the UI."""
    rc, out = ps(script, timeout=45)
    if rc != 0 or not out.strip():
        return ""
    line = out.strip().splitlines()[0].strip()
    bad = ("Exception", "CategoryInfo", "is only supported", "not recognized")
    return "" if any(b in line for b in bad) else line


def collect() -> SysInfo:
    s = SysInfo()

    cpu = _one(
        "$c=Get-CimInstance Win32_Processor|Select-Object -First 1;"
        "\"$($c.Name.Trim())|$($c.NumberOfCores)|$($c.NumberOfLogicalProcessors)\""
    )
    if cpu.count("|") == 2:
        name, cores, threads = cpu.split("|")
        s.cpu = _shorten_cpu(name)
        s.cores = f"{cores}C / {threads}T"

    gpu = _one(
        "$g=Get-CimInstance Win32_VideoController|"
        "Where-Object {$_.AdapterRAM -gt 0}|Select-Object -First 1;"
        "\"$($g.Name)|$([math]::Round($g.AdapterRAM/1GB,1))\""
    )
    if "|" in gpu:
        name, vram = gpu.split("|", 1)
        s.gpu = _shorten_gpu(name)
        try:
            if float(vram) > 0:
                s.vram = f"{float(vram):g} GB"
        except ValueError:
            pass

    ram = _one(
        "$m=Get-CimInstance Win32_PhysicalMemory;"
        "$t=($m|Measure-Object Capacity -Sum).Sum;"
        "$sp=($m|Measure-Object ConfiguredClockSpeed -Maximum).Maximum;"
        "\"$([math]::Round($t/1GB))|$sp\""
    )
    if "|" in ram:
        gb, speed = ram.split("|", 1)
        s.ram = f"{gb} GB"
        if speed.isdigit() and int(speed) > 0:
            s.ram = f"{gb} GB · {speed} MT/s"
            # XMP/EXPO off is the single biggest FPS left on the table
            if int(speed) <= 2400:
                s.warnings.append(
                    f"RAM is running at {speed} MT/s — XMP / EXPO is probably "
                    "off in BIOS. Turning it on beats every tweak in this app."
                )

    hz = _one(
        "$m=Get-CimInstance -Namespace root\\wmi "
        "-ClassName WmiMonitorListedSupportedSourceModes "
        "-ErrorAction SilentlyContinue;"
        "($m.MonitorSourceModes|ForEach-Object{$_.VerticalRefreshRateMaximum}|"
        "Measure-Object -Maximum).Maximum"
    )
    if hz.isdigit() and int(hz) > 0:
        s.refresh_hz = int(hz)
        s.display = f"{hz} Hz"
        s.cap = f"cap {int(hz) - 3} fps"
    else:
        s.display = "unknown"

    osn = _one("(Get-CimInstance Win32_OperatingSystem).Caption")
    s.os_name = osn.replace("Microsoft ", "") if osn else "—"

    rc, pwr = run(["powercfg", "/getactivescheme"])
    if rc == 0 and "(" in pwr:
        s.power = pwr.split("(")[-1].split(")")[0].strip()

    media = _one(
        "(Get-PhysicalDisk|Where-Object{$_.DeviceId -eq 0}|"
        "Select-Object -First 1).MediaType"
    )
    s.disk = media or "—"

    return s


def _shorten_cpu(name: str) -> str:
    for junk in ("(R)", "(TM)", "(tm)", "CPU", "Processor", "with Radeon Graphics"):
        name = name.replace(junk, " ")
    name = name.split("@")[0]
    return " ".join(name.split())


def _shorten_gpu(name: str) -> str:
    for junk in ("NVIDIA ", "AMD ", "Advanced Micro Devices, Inc. ", "(R)", "(TM)"):
        name = name.replace(junk, "")
    return " ".join(name.split())
