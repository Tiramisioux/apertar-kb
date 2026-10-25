# Making a distribution image from the Pi

**Draft, not yet run.** Written 2026-10-25 from what is on the dev Pi today. Turn it into a script once
it has been done by hand once. Model to copy: Cinemate's `make-release-image.sh` (swap config to stock
→ `dd` → PiShrink → `xz` → restore). See the `cinemate-dev` skill, `references/release-image.md`.

## Two kinds of image

| | Personal image | Distribution image |
| --- | --- | --- |
| For | backup of the dev card, or a second card for yourself | other people's cameras |
| Claude login (`~/.claude`) | **kept**: restore it and Claude is still signed in | **removed** |
| KB mirror, VS Code Server, SSH keys, Wi-Fi passwords, history | kept | removed (table below) |
| Who may have it | you only. It holds credentials: private storage, never upload or share | anyone |
| Order | any time | always make a personal image **first**: restoring it is how the dev card gets its setup back |

Both are a `dd` of the whole card from the Mac with the Pi shut down (procedure in the Obsidian
manual, section 11). **Draft, not yet run** (2026-10-25).

- Card from a personal image + the original on the network at once: same hostname
  (`apertar.local`), machine id and SSH host keys. Run one at a time. **probable** conflict, not tested.
- A restored personal image may hold an expired Claude token. Then the extension asks you to sign in
  again. **unconfirmed** how long the token lasts.
- Strip in a plain `ssh apertar` terminal, not a VS Code Remote-SSH window: VS Code would keep its
  server (and Claude Code) running and recreate files under `~/.vscode-server` and `~/.claude`.

## Why the Pi has no GitHub credentials

Anything on the card ships in the image. So the Pi only fetches (HTTPS, public forks), and its
commits are published from the Mac (`working/sync.md`). Keep it that way.

## Strip or reset before imaging

| Item | Where (dev Pi, 2026-10-25) | Action |
| --- | --- | --- |
| Mac's SSH key | `~/.ssh/authorized_keys` | remove (or the image lets your Mac in to every camera) |
| SSH host keys | `/etc/ssh/ssh_host_*` | delete; regenerate on first boot (`sshd` / `raspi-config` does it) **unconfirmed** on trixie |
| Known hosts | `~/.ssh/known_hosts` | remove |
| Wi-Fi passwords | `/etc/NetworkManager/system-connections/` (e.g. `Donii`) | remove everything except `Apertar Hotspot` |
| Hotspot password | `~/.config/CinePi/UI.conf` (`hotspotPassword`, plain text) | reset to the documented default, or set per batch |
| Login password | user `pi` | back to the documented default, or force change on first boot |
| Shell history | `~/.bash_history` | remove |
| VS Code Server | `~/.vscode-server/` (~hundreds of MB) | remove (also removes the Claude Code extension and its bundled `claude` binary) |
| **Claude login** | `~/.claude/.credentials.json`, `~/.claude.json` (signed-in Claude.ai account) | **remove: `rm -rf ~/.claude ~/.claude.json`**. Otherwise every camera ships signed in to your Claude account. Also drops the Pi copy of the `apertar-dev` skill and the chat history |
| Knowledge base | `~/apertar-kb` (your notes, Pi mirror) | sync to the Mac first (`working/sync.md`), then remove |
| Debug leftovers | `~/yank-dmesg.log`, `~/apertar-hardware.conf.bak` | remove |
| Personal hardware config | `~/apertar-hardware.conf` | swap to the stock template for the image, restore after (the Cinemate bracket) |
| Boot config | `/boot/firmware/config.txt` (DPI overlays disabled on this rig) | decide the image's default display; swap to stock, restore after |
| Machine id | `/etc/machine-id` | truncate so each camera gets its own |
| Logs | `/var/log/journal` | vacuum |
| Git identity | `~/.gitconfig` (noreply address) | harmless; remove if the image shouldn't name you |
| Git checkouts | `~/ApertarCore`, `~/ApertarUI`, `~/drivers/imx585-v4l2-driver` | keep or not; remotes are public HTTPS. Make sure `git status` is clean and on the published commit |

## Check the strip worked

```bash
ls -a ~ | grep -iE 'claude|vscode|apertar-kb'     # expect no output
```

## Before imaging, check

- `apertar_status.sh` (on the Mac): every repo `in sync` on GitHub. The image should match a
  published commit; tag it (`image-<version>`) in each fork.
- Both components rebuilt from that commit, services restart cleanly.
- The DKMS imx585 module matches `~/drivers/imx585-v4l2-driver` at the tagged commit.

## Open questions

- Shrink tooling on trixie (PiShrink works on Pi OS images; **unconfirmed** here).
- Image from the running Pi (`dd` of the live root, as Cinemate does) or from a second card?
