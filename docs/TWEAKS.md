# Tweak reference

สร้างจากตาราง step ในโค้ดจริง (`core/profiles.py`) ไม่ใช่เขียนมือ
ถ้าโค้ดเปลี่ยน ให้ regenerate ด้วย `python docs/gen_tweaks.py`

ULTIMATE V2 รัน 14 step · PULSE V2 รัน 18 step และเป็น superset ของ ULTIMATE แบบตรงตัว

## Steps

| # | Step | ULTIMATE | PULSE |
|---|------|:--------:|:-----:|
| 01 | Telemetry & background services | ● | ● |
| 02 | Game DVR & capture stack | ● | ● |
| 03 | Shell & visual effects | ● | ● |
| 04 | Power plan & CPU states | ● | ● |
| 05 | GPU scheduling & shader cache | ● | ● |
| 06 | Network stack & NIC offloads | ● | ● |
| 07 | Input chain | ● | ● |
| 08 | Storage & temp | ● | ● |
| 09 | Thread scheduler & timers | ● | ● |
| 10 | Service trim | ● | ● |
| 11 | Startup & overlays | ● | ● |
| 12 | FiveM cache & launch flags | ● | ● |
| 13 | Defender exclusions | ● | ● |
| 14 | Kernel mitigations | ● | ● |
| 15 | Halt background workloads | — | ● |
| 16 | Latency pass — input & MMCSS | — | ● |
| 17 | QoS DSCP 46 for FiveM / GTA | — | ● |
| 18 | Process reduction | — | ● |

## What each step touches

**Telemetry & background services** — `s_telemetry()`
  
Telemetry, Cortana, Copilot, Recall, Widgets, Start-menu ads, Edge background.

**Game DVR & capture stack** — `s_gamedvr()`
  
Game DVR and the capture stack off. Game Mode stays ON — it is a real scheduler hint.

**Shell & visual effects** — `s_visual()`
  
Visual effects to best-performance, animations and transparency off, shorter kill timeouts.

**Power plan & CPU states** — `s_power()`
  
Ultimate Performance, CPU 100/100, core parking off, USB suspend and PCIe ASPM off, Fast Startup off.

**GPU scheduling & shader cache** — `s_gpu()`
  
HAGS on, longer TDR, NVIDIA telemetry tasks off, stale shader caches wiped.

**Network stack & NIC offloads** — `s_network()`
  
TCP tuned, Nagle off per NIC, NIC offloads and power saving off, MMCSS games task, DNS 1.1.1.1.

**Input chain** — `s_input()`
  
Pointer acceleration off (1:1 mouse), bigger input queues, accessibility key traps off.

**Storage & temp** — `s_storage()`
  
TRIM on, NTFS last-access off, temp / prefetch / INetCache and recycle bin cleared.

**Thread scheduler & timers** — `s_scheduler()`
  
Foreground thread boost and a finer timer resolution.

**Service trim** — `s_services_base()`
  
Trim telemetry, search indexer, Superfetch and Xbox services. Controller service stays Manual.

**Startup & overlays** — `s_startup()`
  
Disable the scheduled telemetry tasks and the GeForce overlay.

**FiveM cache & launch flags** — `s_fivem()`
  
Wipe FiveM caches (keeping the GTA mount), force the discrete GPU, write commandline.txt.

**Defender exclusions** — `s_defender_excl()`
  
RISK — Defender stops scanning the FiveM folder.

**Kernel mitigations** — `s_risk_core()`
  
RISK — Memory Integrity (HVCI) and the Spectre / Meltdown mitigations off.

**Halt background workloads** — `s_pulse_halt()`
  
Stop the background work ULTIMATE leaves running.

**Latency pass — input & MMCSS** — `s_pulse_latency()`
  
Input + system latency pass. Harder than ULTIMATE's.

**QoS DSCP 46 for FiveM / GTA** — `s_pulse_qos()`
  
DSCP 46 (Expedited Forwarding) on the game's UDP traffic.

**Process reduction** — `s_pulse_process()`
  
Fewer processes = fewer context switches.

## Disclosed risks

### ULTIMATE V2

- **Memory Integrity (HVCI) off** — Drivers are no longer hypervisor-verified. A vulnerable or malicious driver gains kernel access. Typical gain: 2–6% when CPU-bound.
- **Spectre / Meltdown mitigations off** — Re-opens CVE-2017-5753 / 5715 / 5754. On Zen 3+ or Intel 10th gen and newer the gain is close to zero — these CPUs fix it in hardware.
- **Windows Defender exclusion on the FiveM folder** — Files in that folder are no longer scanned.

### PULSE V2

- **Memory Integrity (HVCI) off** — Drivers are no longer hypervisor-verified. A vulnerable or malicious driver gains kernel access. Typical gain: 2–6% when CPU-bound.
- **Spectre / Meltdown mitigations off** — Re-opens CVE-2017-5753 / 5715 / 5754. On Zen 3+ or Intel 10th gen and newer the gain is close to zero — these CPUs fix it in hardware.
- **Windows Defender exclusion on the FiveM folder** — Files in that folder are no longer scanned.
- **Windows Update paused 35 days** — No security patches until it resumes. It resumes on its own.
- **File sharing, RDP and printing disabled** — Shared folders, Remote Desktop and all printers stop working.
- **Memory compression and Superfetch off** — On 16 GB or less this usually makes stutter WORSE, not better.
- **IPv6 disabled** — Any IPv6-only server or service becomes unreachable.

