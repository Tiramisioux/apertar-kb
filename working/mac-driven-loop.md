# Developing from the Mac, testing on the Pi

Decided 2026-10-26 (Patrik): run the `apertar-dev` skill and Claude Code on the **Mac**, drive the Pi over ssh (`apertar`).
Do not run Claude Code, VS Code Remote-SSH or the C++ language server on the Pi while measuring.

## Why (CONFIRMED on the Pi, 2026-10-26 19:56)

With VS Code Remote and Claude running on the Pi, `cpptools-srv` held 982 MB and averaged 38.6 % of a core since it
started after the reboot; the VS Code server held another 453 MB, `claude` 276 MB. The Pi had 131 MB free and 707 MB of
swap in use, while the 25/30 fps takes lost more frames than the same cases earlier the same day (uncompressed 25 fps:
0,0,0,0,6 missing earlier; 0,39,37 after). Whether that load caused the loss is **unconfirmed**; it is a confound, and
the 4 GB board cannot carry the dev tools and a clean measurement together.

## The loop (PROBABLE: from `workspace-contract.md` and `sync.md`; not yet run end to end)

1. Mac: `git -C ~/Documents/Apertar/Apertar-Core fetch ssh://apertar/home/pi/ApertarCore clearhdr-fixes:clearhdr-fixes`
   (one-off, brings the Pi-only T23 commit `db17860` over. Read-only on the Pi).
2. Mac: edit and commit on branch `clearhdr-fixes`. The work stays off GitHub: never push this branch to `origin`.
3. To the Pi: the `pi` remote's push URL is a deliberate dud. Push to an explicit URL and to a **staging name**, not to the
   branch checked out on the Pi, then fast-forward on the Pi. Patrik decides each time; this bypasses a safeguard on
   purpose. Scripted (2026-10-26): `~/.claude/skills/apertar-dev/scripts/apertar_push_to_pi.sh core clearhdr-fixes`
   (`--dry-run` first). It refuses on Pi-only commits, a dirty Pi tree or a non-fast-forward.
4. Build on the Pi only: `ssh apertar 'cmake --build ~/ApertarCore-build -j2'` (no build while a take runs).
5. Restart is Patrik's (`sudo`): `sudo systemctl restart apertar-core`.
6. Test over ssh: `bash ~/apertar-kb/working/tools/takes.sh 5 10` and `core.py`, with nothing else running on the Pi.
7. `apertar_publish.sh` moves `main` only, so it does not touch `clearhdr-fixes`.

## Open

- ~~The Mac skill file did not match this loop~~ Done 2026-10-26: `SKILL.md`, `SKILL.pi.md` and `workspace-contract.md` describe it.
- Tutorial progress is written on the machine that runs `tutorial.py`: with the Mac-first loop that is the Mac (it reads the Pi over ssh), so progress is already in the Mac KB and `apertar_publish.sh kb` sends it on. Pi-side runs still go via `deploy_to_pi.sh` (**unconfirmed** end to end).
  `deploy_to_pi.sh`. How progress travels Mac to Pi is **unconfirmed**.
- Pending KB entries: `hardware-log.md` follow-up for the uncompressed results (25 fps clean in 4 of 5 earlier takes, 30 fps
  loses ~51), the amendment that the T22 takes were lossless-JPEG (encoder capacity ~18 fps per Core's own
  `estimated_capacity_fps`), and the unplanned NVMe drop at 19:35:32 (`CSTS=0xffffffff`, recovered by PCIe re-init).
- Boot arguments `nvme_core.default_ps_max_latency_us=0 pcie_aspm=off` are in `cmdline.txt` (backup
  `cmdline.txt.bak-20261026`); no further drop seen in about 8 minutes of idle watching; not a long enough test.
