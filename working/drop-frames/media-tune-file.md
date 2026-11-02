# The media tuning file `~/apertar-media-tune.conf` (design, 2026-11-02)

Status: **being built** (Core `drop-frames`, after `48f8b8c`; CLI `scripts/apertar-tune`). Asked for by Patrik on
2026-11-02 after B1: the campaign's findings go into a settings file per storage medium, next to the hardware
conf, and test nights must be able to override it from the command line. Fork-only: media profiles
(`src/util/MediaProfile.hpp`, `26da30e`) are not in upstream Apertar or in the fork's `main`.

## Why a file

Until now every write-path knob was an environment variable of the Core service (systemd drop-ins:
`APERTAR_DNG_DONTNEED`, `APERTAR_DNG_WRITEBACK`, `APERTAR_MEDIA_SYNC_MS`, `APERTAR_RAW_CAMERA_BUFFERS`,
`APERTAR_MEDIA_TUNE`), and the writer topology per filesystem (workers, queue, extra raw buffers) was a table in
`MediaProfile.hpp`. A file per medium puts the camera's tuning in one readable place, editable without sudo; the
environment variables stay as the A/B instruments (they win).

## Decisions (the lead's, following the existing patterns)

- **Name and place**: `/home/pi/apertar-media-tune.conf`, beside `/home/pi/apertar-hardware.conf` and in its INI
  format. `.conf` added to the asked-for name: it matches the hardware conf and keeps it apart from the root helper
  `/usr/local/libexec/apertar-media-tune`. Template in Core: `config/apertar-media-tune.conf`.
- **Sections**: `[default]`, `[<filesystem>]` (exfat, ext4, vfat, ntfs, ntfs-fuse, other), `[<connection>]`
  (pi-nvme, usb-uas, usb-storage, sd-card, other), `[<connection>.<filesystem>]`. The most specific wins.
  Media only, not per recording format: no test has shown a format needs its own value yet.
- **Keys**: `dontneed` (sync|writer|off), `writeback` (on|off), `sync_ms` (0-60000), `raw_buffers` (3-16),
  `extra_raw_buffers` (0-8), `workers` (1-8), `queue` (4-64), `kernel_tune` (on|off). Bad values are ignored with
  a journal warning.
- **Override for test nights**: `/dev/shm/apertar-media-tune.override.conf`, same format, on top of the file. tmpfs:
  a reboot removes it, so a shoot never inherits a test setting by accident. Edited with `scripts/apertar-tune`
  (`show`, `set key=value [--section S]`, `unset`, `clear`, `init`), unprivileged.
- **Precedence**: environment variable > override file > base file > code default.
- **When it applies**: read when Core starts (the page-cache mode and the writeback hint are fixed per process):
  a change needs a Core restart; `b1-arm.sh` restarts Core per arm anyway.
- **Self-describing**: Core logs `ApertarCore media tune: file=... override=... <every key> source: ...` once per
  start; every `recording clip:` line gains ` tune_override=<yes|no>`.

## The values written (the campaign's findings as of 2026-11-02)

`[default] dontneed=sync writeback=on sync_ms=1000 raw_buffers=8 kernel_tune=off`; `[exfat]` and `[ext4]`
`workers=4 queue=12 extra_raw_buffers=0`. This is exactly what the camera ran during B1 (the 8 raw buffers came from
the `/etc` drop-in `zz-ladder-buffers.conf`; Clear HDR has 8 by default, SDR 4). Only `dontneed=sync` is
test-backed (B1, p = 1/36); the rest is the current state, not a measured optimum. `kernel_tune` stays off until B3
shows a kernel setting helping. The raw buffer count is the first candidate for a test (every lost frame in B1 was
a raw-buffer starvation, [tests-2026-11/findings-2026-11-02.md](tests-2026-11/findings-2026-11-02.md)).

## Restore list addition

End of every test evening: `scripts/apertar-tune clear` (or a reboot), then a Core restart.
