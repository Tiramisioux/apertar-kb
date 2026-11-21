# Setup beyond the code

For the Apertar developer. What a camera needs besides the new binaries, for the branch `cinemate-port` (clip folder split included) with the review fixes.

A stock camera needs **nothing** from this list. It behaves as Apertar 1.6.0. Each item turns on one feature.

| Page | What it covers |
| --- | --- |
| [services.md](services.md) | systemd units and drop-ins |
| [root-helpers.md](root-helpers.md) | small root scripts, sudoers rules, a tmpfiles rule |
| [config-files.md](config-files.md) | new sections in `apertar-hardware.conf`, and the other files |
| [environment.md](environment.md) | switches set in Core's environment |
| [boot-and-tuning.md](boot-and-tuning.md) | `config.txt` and libcamera files |
| [walkthrough.md](walkthrough.md) | a short tour of what cinemate-port adds |

The touch UI needs nothing new. Build it and install it as before.

Paths assume user `pi`, the Core repo in `~/ApertarCore` and the build in `~/ApertarCore-build`, as in 1.6.0.
