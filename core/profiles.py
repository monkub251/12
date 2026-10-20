"""
Profile definitions.

ULTIMATE V2 — full system tuning. Throughput / FPS character.
PULSE V2    — everything in ULTIMATE, then squeezed further for latency:
              background work stopped, UDP prioritised, process count reduced.

Both profiles include tweaks that reduce the machine's security posture.
Those are tagged RISK and surfaced to the user before the run starts.
Everything is recorded to a snapshot and reversed by GLOBAL RESET.
"""

from __future__ import annotations

import os
from pathlib import Path

from .engine import Ctx, find_fivem, ps, run, wipe_dir

MM = r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
MEMMGR = r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
KERNEL = r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\kernel"


# ===========================================================================
# shared blocks
# ===========================================================================


def s_telemetry(c: Ctx):
    """Telemetry, Cortana, Copilot, Recall, Widgets, Start-menu ads, Edge background."""
    dc = r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection"
    c.reg(dc, "AllowTelemetry", 0, note="telemetry off")
    c.reg(dc, "DoNotShowFeedbackNotifications", 1)
    ws = r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Windows Search"
    c.reg(ws, "AllowCortana", 0, note="Cortana off")
    c.reg(ws, "AllowSearchToUseLocation", 0)
    c.reg(ws, "DisableWebSearch", 1, note="web results off")
    c.reg(ws, "ConnectedSearchUseWeb", 0)
    c.reg(
        r"HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot",
        "TurnOffWindowsCopilot", 1, note="Copilot off",
    )
    c.reg(
        r"HKCU\Software\Policies\Microsoft\Windows\WindowsCopilot",
        "TurnOffWindowsCopilot", 1,
    )
    c.reg(
        r"HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsAI",
        "DisableAIDataAnalysis", 1, note="Recall off",
    )
    c.reg(r"HKLM\SOFTWARE\Policies\Microsoft\Dsh", "AllowNewsAndInterests", 0,
          note="Widgets off")

    cdm = r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
    for v in (
        "SilentInstalledAppsEnabled", "SystemPaneSuggestionsEnabled",
        "SoftLandingEnabled", "PreInstalledAppsEnabled",
        "OemPreInstalledAppsEnabled", "RotatingLockScreenOverlayEnabled",
        "SubscribedContent-338388Enabled", "SubscribedContent-338389Enabled",
        "SubscribedContent-310093Enabled",
    ):
        c.reg(cdm, v, 0)
    c.reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
          "Enabled", 0, note="ad ID off")
    c.reg(r"HKLM\SOFTWARE\Policies\Microsoft\Edge", "StartupBoostEnabled", 0,
          note="Edge startup boost off")
    c.reg(r"HKLM\SOFTWARE\Policies\Microsoft\Edge", "BackgroundModeEnabled", 0)


def s_gamedvr(c: Ctx):
    """Game DVR and the capture stack off. Game Mode stays ON — it is a real scheduler hint."""
    c.reg(r"HKCU\System\GameConfigStore", "GameDVR_Enabled", 0, note="Game DVR off")
    c.reg(r"HKCU\System\GameConfigStore", "GameDVR_FSEBehaviorMode", 2)
    c.reg(r"HKCU\System\GameConfigStore", "GameDVR_HonorUserFSEBehaviorMode", 1)
    c.reg(r"HKCU\System\GameConfigStore", "GameDVR_DXGIHonorFSEWindowsCompatible", 1)
    c.reg(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0)
    gb = r"HKCU\Software\Microsoft\GameBar"
    c.reg(gb, "UseNexusForGameBarEnabled", 0)
    c.reg(gb, "ShowStartupPanel", 0)
    # Game Mode stays ON — it is a real scheduler hint
    c.reg(gb, "AutoGameModeEnabled", 1, note="Game Mode on")
    c.reg(gb, "AllowAutoGameMode", 1)
    c.reg(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
        "GlobalUserDisabled", 1, note="UWP background apps off",
    )


def s_visual(c: Ctx):
    """Visual effects to best-performance, animations and transparency off, shorter kill timeouts."""
    c.reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
          "VisualFXSetting", 2, note="best performance")
    d = r"HKCU\Control Panel\Desktop"
    c.reg(d, "MenuShowDelay", "0", "sz", "menu delay 0ms")
    c.reg(d, "DragFullWindows", "0", "sz")
    c.reg(d, "AutoEndTasks", "1", "sz")
    c.reg(d, "HungAppTimeout", "2000", "sz")
    c.reg(d, "WaitToKillAppTimeout", "2000", "sz")
    c.reg(r"HKCU\Control Panel\Desktop\WindowMetrics", "MinAnimate", "0", "sz",
          "window animation off")
    c.reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
          "EnableTransparency", 0, note="transparency off")
    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Control", "WaitToKillServiceTimeout",
          "2000", "sz", "faster shutdown")


def s_power(c: Ctx):
    """Ultimate Performance, CPU 100/100, core parking off, USB suspend and PCIe ASPM off, Fast Startup off."""
    rc, out = c.powercfg("/getactivescheme")
    scheme = ""
    for tok in out.replace(":", " ").split():
        if len(tok) == 36 and tok.count("-") == 4:
            scheme = tok
            break
    if scheme:
        c.backup.set("power", "old_scheme", scheme)
        c.info(f"current scheme saved: {scheme}")

    ULT = "e9a42b02-d5df-448d-aa00-03f14749eb61"
    rc, out = c.powercfg("-duplicatescheme", ULT)
    guid = ""
    for tok in out.replace(":", " ").split():
        if len(tok) == 36 and tok.count("-") == 4:
            guid = tok
            break
    if not guid:
        rc, lst = c.powercfg("/list")
        for line in lst.splitlines():
            if "Ultimate" in line:
                for tok in line.split():
                    if len(tok) == 36 and tok.count("-") == 4:
                        guid = tok
                        break
    if guid:
        c.powercfg("/setactive", guid)
        c.ok("Ultimate Performance active")
    else:
        c.powercfg("/setactive", "SCHEME_MIN")
        c.warn("Ultimate unavailable — High Performance active")

    # unhide then set the hidden processor settings
    c.powercfg("-attributes", "SUB_PROCESSOR",
               "0cc5b647-c1df-4637-891a-dec35c318583", "-ATTRIB_HIDE")
    c.powercfg("-attributes", "SUB_PROCESSOR",
               "5d76a2ca-e8c0-402f-a133-2158492d58ad", "-ATTRIB_HIDE")

    pairs = [
        ("SUB_PROCESSOR", "PROCTHROTTLEMIN", "100"),
        ("SUB_PROCESSOR", "PROCTHROTTLEMAX", "100"),
        ("SUB_PROCESSOR", "CPMINCORES", "100"),
        ("2a737441-1930-4402-8d77-b2bebba308a3",
         "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", "0"),
        ("501a4d13-42af-4429-9fd1-a8218c268e20",
         "ee12f906-d277-404b-b6da-e5fa1a576df5", "0"),
        ("SUB_DISK", "DISKIDLE", "0"),
        ("SUB_VIDEO", "VIDEOIDLE", "0"),
    ]
    for sub, setting, val in pairs:
        c.powercfg("-setacvalueindex", "SCHEME_CURRENT", sub, setting, val)
    c.powercfg("/setactive", "SCHEME_CURRENT")
    c.ok("core parking off · CPU 100/100 · USB suspend off · PCIe ASPM off")

    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Control\Power", "HiberbootEnabled", 0,
          note="Fast Startup off")


def s_gpu(c: Ctx):
    """HAGS on, longer TDR, NVIDIA telemetry tasks off, stale shader caches wiped."""
    gd = r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers"
    c.reg(gd, "HwSchMode", 2, note="HAGS on")
    c.reg(gd, "TdrDelay", 10)

    ps(
        "Get-ScheduledTask -TaskName 'Nv*' -ErrorAction SilentlyContinue | "
        "Where-Object { $_.TaskName -match 'Tm|Telemetry|Profile' } | "
        "Disable-ScheduledTask -ErrorAction SilentlyContinue | Out-Null"
    )
    c.ok("NVIDIA telemetry tasks disabled")
    c.reg(r"HKLM\SOFTWARE\NVIDIA Corporation\NvControlPanel2\Client",
          "OptInOrOutPreference", 0, note="NVIDIA telemetry opt-out")

    la = os.environ.get("LOCALAPPDATA", "")
    freed = 0
    for p in (
        Path(la) / "NVIDIA" / "DXCache",
        Path(la) / "NVIDIA" / "GLCache",
        Path(la) / "AMD" / "DxCache",
        Path(la) / "D3DSCache",
    ):
        freed += wipe_dir(p)
    c.ok(f"shader caches cleared — {freed / 1048576:.0f} MB")


def s_network(c: Ctx):
    """TCP tuned, Nagle off per NIC, NIC offloads and power saving off, MMCSS games task, DNS 1.1.1.1."""
    rc, out = run(["netsh", "int", "tcp", "show", "global"])
    for line in out.splitlines():
        if "Auto-Tuning" in line and ":" in line:
            c.backup.set("netsh", "autotuning", line.split(":")[-1].strip())
            break

    for a in (
        "autotuninglevel=normal",
        "rss=enabled",
        "ecncapability=disabled",
        "timestamps=disabled",
        "nonsackrttresiliency=disabled",
    ):
        run(["netsh", "int", "tcp", "set", "global", a])
    run(["netsh", "int", "tcp", "set", "supplemental", "Internet",
         "congestionprovider=ctcp"])
    c.ok("TCP tuned — autotuning normal · RSS on · ECN/timestamps off")

    # Nagle off per live interface
    rc, out = ps(
        "Get-NetAdapter | Where-Object Status -eq 'Up' | "
        "ForEach-Object { $_.Name + '|' + $_.InterfaceGuid }"
    )
    adapters = []
    for line in out.splitlines():
        if "|" in line:
            name, guid = line.strip().split("|", 1)
            adapters.append((name.strip(), guid.strip()))

    base = r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
    for name, guid in adapters:
        c.reg(f"{base}\\{guid}", "TcpAckFrequency", 1, note=f"Nagle off · {name}")
        c.reg(f"{base}\\{guid}", "TCPNoDelay", 1)
        c.reg(f"{base}\\{guid}", "TcpDelAckTicks", 0)

    c.reg(MM, "NetworkThrottlingIndex", 0xFFFFFFFF, note="network throttling off")
    c.reg(MM, "SystemResponsiveness", 10, note="MMCSS reserve 10%")
    games = MM + r"\Tasks\Games"
    c.reg(games, "GPU Priority", 8)
    c.reg(games, "Priority", 6)
    c.reg(games, "Scheduling Category", "High", "sz")
    c.reg(games, "SFIO Priority", "High", "sz")
    c.reg(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Psched",
          "NonBestEffortLimit", 0, note="QoS reserve 0%")

    kill = [
        "Energy-Efficient Ethernet", "Energy Efficient Ethernet",
        "Green Ethernet", "Power Saving Mode", "Gigabit Lite",
        "Flow Control", "Interrupt Moderation", "Ultra Low Power Mode",
        "Advanced EEE", "ARP Offload", "NS Offload", "Selective Suspend",
    ]
    for name, _ in adapters:
        for prop in kill:
            rc, out = ps(
                f'$p = Get-NetAdapterAdvancedProperty -Name "{name}" '
                f'-DisplayName "{prop}" -ErrorAction SilentlyContinue; '
                f"if ($p) {{ $p.DisplayValue; "
                f'Set-NetAdapterAdvancedProperty -Name "{name}" '
                f'-DisplayName "{prop}" -DisplayValue "Disabled" -NoRestart '
                f"-ErrorAction SilentlyContinue }}"
            )
            val = out.strip().splitlines()
            if val:
                c.backup.nic(name, prop, val[0].strip())
                c.ok(f"nic  {name}: {prop} off")
        ps(
            f'Set-NetAdapterPowerManagement -Name "{name}" '
            f"-AllowComputerToTurnOffDevice Disabled -ErrorAction SilentlyContinue"
        )

    ps(
        "Get-NetAdapter | Where-Object Status -eq 'Up' | "
        "Set-DnsClientServerAddress -ServerAddresses ('1.1.1.1','8.8.8.8') "
        "-ErrorAction SilentlyContinue"
    )
    run(["ipconfig", "/flushdns"])
    c.ok("DNS -> 1.1.1.1 / 8.8.8.8 · cache flushed")


def s_input(c: Ctx):
    """Pointer acceleration off (1:1 mouse), bigger input queues, accessibility key traps off."""
    m = r"HKCU\Control Panel\Mouse"
    c.reg(m, "MouseSpeed", "0", "sz", "pointer acceleration OFF")
    c.reg(m, "MouseThreshold1", "0", "sz")
    c.reg(m, "MouseThreshold2", "0", "sz")
    c.reg(m, "MouseSensitivity", "10", "sz", "6/11 = no scaling")
    c.reg(m, "MouseHoverTime", "10", "sz")

    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Services\mouclass\Parameters",
          "MouseDataQueueSize", 20)
    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Services\kbdclass\Parameters",
          "KeyboardDataQueueSize", 20)

    k = r"HKCU\Control Panel\Keyboard"
    c.reg(k, "KeyboardDelay", "0", "sz", "repeat delay min")
    c.reg(k, "KeyboardSpeed", "31", "sz", "repeat rate max")

    acc = r"HKCU\Control Panel\Accessibility"
    c.reg(acc + r"\StickyKeys", "Flags", "506", "sz", "Sticky Keys off")
    c.reg(acc + r"\Keyboard Response", "Flags", "122", "sz", "Filter Keys off")
    c.reg(acc + r"\ToggleKeys", "Flags", "58", "sz", "Toggle Keys off")


def s_storage(c: Ctx):
    """TRIM on, NTFS last-access off, temp / prefetch / INetCache and recycle bin cleared."""
    run(["fsutil", "behavior", "set", "DisableDeleteNotify", "0"])
    c.ok("TRIM enabled")

    rc, out = run(["fsutil", "behavior", "query", "disablelastaccess"])
    old = "2"
    if "=" in out:
        tail = out.split("=")[-1].strip().split()
        if tail and tail[0].isdigit():
            old = tail[0]
    c.backup.set("fsutil", "last_access", old)
    run(["fsutil", "behavior", "set", "disablelastaccess", "1"])
    c.ok("NTFS last-access timestamp off")

    freed = 0
    for p in (
        Path(os.environ.get("TEMP", "")),
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Temp",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Prefetch",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "INetCache",
    ):
        freed += wipe_dir(p)
    c.ok(f"temp files cleared — {freed / 1048576:.0f} MB")

    ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
    c.ok("recycle bin emptied")


def s_scheduler(c: Ctx):
    """Foreground thread boost and a finer timer resolution."""
    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl",
          "Win32PrioritySeparation", 38, note="foreground boost 3:1")
    c.reg(KERNEL, "GlobalTimerResolutionRequests", 1, note="allow 0.5ms timer")
    c.reg(KERNEL, "SerializeTimerExpiration", 1)


def s_services_base(c: Ctx):
    """Trim telemetry, search indexer, Superfetch and Xbox services. Controller service stays Manual."""
    for name, note in [
        ("DiagTrack", "Connected User Experiences"),
        ("dmwappushservice", ""),
        ("diagnosticshub.standardcollector.service", ""),
        ("SysMain", "Superfetch"),
        ("WSearch", "search indexer"),
        ("MapsBroker", ""),
        ("RetailDemo", ""),
        ("RemoteRegistry", ""),
        ("Fax", ""),
        ("XblAuthManager", ""),
        ("XblGameSave", ""),
        ("XboxNetApiSvc", ""),
    ]:
        c.service(name, "disabled", note=note)
    c.service("XboxGipSvc", "demand", stop=False, note="kept Manual — controllers")


def s_startup(c: Ctx):
    """Disable the scheduled telemetry tasks and the GeForce overlay."""
    for t in (
        r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraisal",
        r"\Microsoft\Windows\Application Experience\ProgramDataUpdater",
        r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
        r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
        r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
        r"\Microsoft\Windows\Feedback\Siuf\DmClient",
        r"\Microsoft\Windows\Windows Error Reporting\QueueReporting",
    ):
        c.task_off(t)

    c.reg(r"HKCU\Software\NVIDIA Corporation\Global\NVTweak",
          "NvCplDisableOverlay", 1, note="GeForce overlay off")
    c.info("Discord / Medal overlays: turn off inside each app")


def s_fivem(c: Ctx):
    """Wipe FiveM caches (keeping the GTA mount), force the discrete GPU, write commandline.txt."""
    root = c.fivem_path or find_fivem()
    if not root:
        c.warn("FiveM folder not found — cache step skipped")
        return
    c.fivem_path = root
    c.info(f"FiveM root: {root}")

    app = root / "FiveM.app"
    if not app.exists():
        app = root

    total = 0
    for name in ("cache", "server-cache", "server-cache-priv", "crashes", "logs"):
        p = app / "data" / name
        if not p.exists():
            p = app / name
        if p.exists():
            # 'game' inside cache is the GTA mount — wiping it forces a full redownload
            freed = wipe_dir(p, keep={"game"})
            total += freed
            c.ok(f"cache cleared: {name} — {freed / 1048576:.0f} MB")
    c.ok(f"FiveM cache freed ~{total / 1048576:.0f} MB")

    exe = root / "FiveM.exe"
    if exe.exists():
        c.reg(r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers",
              str(exe), "~ DISABLEDXMAXIMIZEDWINDOWEDMODE HIGHDPIAWARE", "sz",
              "fullscreen optimizations off")
        c.reg(r"HKCU\Software\Microsoft\DirectX\UserGpuPreferences",
              str(exe), "GpuPreference=2;", "sz", "force discrete GPU")

    cl = root / "commandline.txt"
    try:
        if cl.exists():
            cl.replace(root / f"commandline.txt.bak-{c.backup.stamp}")
        cl.write_text("-notablet", encoding="ascii")
        c.ok("commandline.txt written: -notablet")
    except Exception as e:  # noqa: BLE001
        c.warn(f"commandline.txt failed: {e}")


# ===========================================================================
# RISK blocks — security posture reduced, all reversible
# ===========================================================================


def s_risk_core(c: Ctx):
    """RISK — Memory Integrity (HVCI) and the Spectre / Meltdown mitigations off."""
    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios"
          r"\HypervisorEnforcedCodeIntegrity", "Enabled", 0,
          note="Memory Integrity off")
    c.reg(MEMMGR, "FeatureSettingsOverride", 3, note="Spectre/Meltdown mitigations off")
    c.reg(MEMMGR, "FeatureSettingsOverrideMask", 3)


def s_defender_excl(c: Ctx):
    """RISK — Defender stops scanning the FiveM folder."""
    paths = [str(Path(os.environ.get("LOCALAPPDATA", "")) / "FiveM")]
    if c.fivem_path:
        paths.append(str(c.fivem_path))
    for p in paths:
        rc, _ = ps(f'Add-MpPreference -ExclusionPath "{p}" -ErrorAction SilentlyContinue')
        c.ok(f"Defender exclusion: {p}")


# ===========================================================================
# PULSE-only blocks
# ===========================================================================


def s_pulse_halt(c: Ctx):
    """Stop the background work ULTIMATE leaves running."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    until = now + timedelta(days=35)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    ux = r"HKLM\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
    c.reg(ux, "PauseFeatureUpdatesStartTime", now.strftime(fmt), "sz")
    c.reg(ux, "PauseFeatureUpdatesEndTime", until.strftime(fmt), "sz")
    c.reg(ux, "PauseQualityUpdatesStartTime", now.strftime(fmt), "sz")
    c.reg(ux, "PauseQualityUpdatesEndTime", until.strftime(fmt), "sz",
          "Windows Update paused 35d")
    c.reg(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate",
          "ExcludeWUDriversInQualityUpdate", 1, note="no auto driver updates")

    for name, note in [
        ("Spooler", "printing"),
        ("TermService", "RDP"),
        ("LanmanServer", "file sharing"),
        ("WerSvc", "error reporting"),
        ("PcaSvc", "program compatibility"),
        ("WbioSrvc", "biometrics"),
        ("TabletInputService", "touch keyboard"),
    ]:
        c.service(name, "disabled", note=note)


def s_pulse_latency(c: Ctx):
    """Input + system latency pass. Harder than ULTIMATE's."""
    c.reg(MM, "SystemResponsiveness", 0, note="MMCSS reserve 0% — all to foreground")
    games = MM + r"\Tasks\Games"
    c.reg(games, "Priority", 8, note="games task max priority")
    c.reg(games, "Clock Rate", 10000)
    c.reg(games, "Affinity", 0)
    c.reg(games, "Background Only", "False", "sz")

    c.reg(KERNEL, "DistributeTimers", 1, note="timers spread across cores")
    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl",
          "Win32PrioritySeparation", 22, note="longer quantum, hard fg bias")

    # USB / HID power gating off — removes wake latency on input devices
    ps(
        "Get-WmiObject MSPower_DeviceEnable -Namespace root\\wmi | "
        "ForEach-Object { $_.Enable = $false; $_.Put() } 2>$null | Out-Null"
    )
    c.ok("USB/HID selective power-down disabled")

    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Services\USB", "DisableSelectiveSuspend", 1)


def s_pulse_qos(c: Ctx):
    """DSCP 46 (Expedited Forwarding) on the game's UDP traffic."""
    qos = r"HKLM\SOFTWARE\Policies\Microsoft\Windows\QoS"
    for label, exe in (("BANNARAKX-FiveM", "FiveM.exe"),
                       ("BANNARAKX-FiveM-Game", "FiveM_GTAProcess.exe"),
                       ("BANNARAKX-GTA5", "GTA5.exe")):
        k = f"{qos}\\{label}"
        c.reg(k, "Version", "1.0", "sz")
        c.reg(k, "Application Name", exe, "sz")
        c.reg(k, "Protocol", "UDP", "sz")
        c.reg(k, "Local Port", "*", "sz")
        c.reg(k, "Local IP", "*", "sz")
        c.reg(k, "Local IP Prefix Length", "*", "sz")
        c.reg(k, "Remote Port", "*", "sz")
        c.reg(k, "Remote IP", "*", "sz")
        c.reg(k, "Remote IP Prefix Length", "*", "sz")
        c.reg(k, "DSCP Value", "46", "sz", f"EF marking · {exe}")
        c.reg(k, "Throttle Rate", "-1", "sz")

    # policy-based QoS is ignored without this
    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\QoS",
          "Do not use NLA", "1", "sz", "apply QoS on all networks")
    c.info("DSCP 46 only helps if your router honours it — check its QoS page")


def s_pulse_process(c: Ctx):
    """Fewer processes = fewer context switches."""
    ram_kb = 0
    rc, out = ps("(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory")
    try:
        ram_kb = int(out.strip()) // 1024
    except Exception:  # noqa: BLE001
        ram_kb = 16 * 1024 * 1024
    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Control",
          "SvcHostSplitThresholdInKB", ram_kb,
          note="svchost grouped into one process")

    c.reg(r"HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting",
          "Disabled", 1, note="WER off")
    c.reg(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\Explorer",
          "DisableSearchBoxSuggestions", 1, note="search web suggestions off")
    c.reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search",
          "BingSearchEnabled", 0)
    c.reg(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search",
          "CortanaConsent", 0)

    c.reg(MEMMGR, "LargeSystemCache", 0)
    c.reg(MEMMGR + r"\PrefetchParameters", "EnablePrefetcher", 0)
    c.reg(MEMMGR + r"\PrefetchParameters", "EnableSuperfetch", 0)

    rc, out = ps("(Get-MMAgent).MemoryCompression")
    c.backup.set("mmagent", "memory_compression", "True" in out)
    ps("Disable-MMAgent -mc -ErrorAction SilentlyContinue")
    c.ok("memory compression off")

    c.reg(r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters",
          "DisabledComponents", 0xFF, note="IPv6 off")


# ===========================================================================
# profile tables
# ===========================================================================

ULTIMATE_STEPS = [
    ("Telemetry & background services", s_telemetry),
    ("Game DVR & capture stack", s_gamedvr),
    ("Shell & visual effects", s_visual),
    ("Power plan & CPU states", s_power),
    ("GPU scheduling & shader cache", s_gpu),
    ("Network stack & NIC offloads", s_network),
    ("Input chain", s_input),
    ("Storage & temp", s_storage),
    ("Thread scheduler & timers", s_scheduler),
    ("Service trim", s_services_base),
    ("Startup & overlays", s_startup),
    ("FiveM cache & launch flags", s_fivem),
    ("Defender exclusions", s_defender_excl),
    ("Kernel mitigations", s_risk_core),
]

PULSE_STEPS = ULTIMATE_STEPS + [
    ("Halt background workloads", s_pulse_halt),
    ("Latency pass — input & MMCSS", s_pulse_latency),
    ("QoS DSCP 46 for FiveM / GTA", s_pulse_qos),
    ("Process reduction", s_pulse_process),
]


PROFILES = {
    "ULTIMATE": {
        "name": "ULTIMATE V2",
        "index": "01",
        "sub": "FULL SYSTEM TUNING",
        "blurb": (
            "ปรับทั้งระบบเพื่อ FPS สูงสุดและเฟรมนิ่ง: power plan, GPU scheduling, "
            "network stack, input chain, scheduler และล้างแคช FiveM "
            "ย้อนกลับได้ด้วย GLOBAL RESET"
        ),
        "bullets": [
            "Power · CPU 100/100 · core parking off · PCIe ASPM off",
            "GPU HAGS · shader cache wipe · NVIDIA telemetry off",
            "Network stack · Nagle off · NIC offloads off · DNS 1.1.1.1",
            "Input 1:1 · mouse accel off · queue size · FiveM cache wipe",
        ],
        "steps": ULTIMATE_STEPS,
        "impact": "HIGH IMPACT",
    },
    "PULSE": {
        "name": "PULSE V2",
        "index": "02",
        "sub": "MAX · FULL SYSTEM",
        "blurb": (
            "โหมดเต็มระบบที่แรงกว่า ULTIMATE: ทุกอย่างของ ULTIMATE แล้วบีบ"
            "ระบบเพิ่มอีกชั้น ปิดงานเบื้องหลัง ลดโปรเซส และจูนอินพุตกับ"
            "เครือข่ายสำหรับ FiveM สุดขั้ว ย้อนกลับได้ด้วย GLOBAL RESET"
        ),
        "bullets": [
            "ทุกอย่างของ ULTIMATE + หยุด Windows Update · Printing · RDP · File sharing",
            "Input + system latency (Game DVR off · MMCSS Games)",
            "QoS DSCP 46 สำหรับ FiveM / GTA (UDP)",
            "Process reduce (svchost รวม · ปิด WER · Search เว็บ · แอปเบื้องหลัง)",
        ],
        "steps": PULSE_STEPS,
        "impact": "HIGH IMPACT",
    },
}


_RISK_SHARED = [
    ("Memory Integrity (HVCI) off",
     "Drivers are no longer hypervisor-verified. A vulnerable or malicious "
     "driver gains kernel access. Typical gain: 2–6% when CPU-bound."),
    ("Spectre / Meltdown mitigations off",
     "Re-opens CVE-2017-5753 / 5715 / 5754. On Zen 3+ or Intel 10th gen and "
     "newer the gain is close to zero — these CPUs fix it in hardware."),
    ("Windows Defender exclusion on the FiveM folder",
     "Files in that folder are no longer scanned."),
]

RISK_NOTICE = {
    "ULTIMATE": _RISK_SHARED,
    "PULSE": _RISK_SHARED + [
        ("Windows Update paused 35 days",
         "No security patches until it resumes. It resumes on its own."),
        ("File sharing, RDP and printing disabled",
         "Shared folders, Remote Desktop and all printers stop working."),
        ("Memory compression and Superfetch off",
         "On 16 GB or less this usually makes stutter WORSE, not better."),
        ("IPv6 disabled",
         "Any IPv6-only server or service becomes unreachable."),
    ],
}
