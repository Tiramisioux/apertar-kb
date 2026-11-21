# Extra files: where to place them

The non-code files of Apertar Core (review branch `claude/awesome-pasteur-qzsiow`, `57da4eb`). In the repo they sit in `config/` and `scripts/`.

A stock camera needs none of them. Each group turns on one feature. Install only the groups you want.

Copy the folder to the Pi, then run the commands from inside it:

```bash
cd ~/apertar-extra-files
```

## Overview

| File | Place it in | Owner, mode | Feature |
| --- | --- | --- | --- |
| `scripts/start-apertar-core.sh` | `/home/pi/start-apertar-core.sh` | pi, 0755 | start script (both Cores) |
| `config/apertar-core-cam1.service` | `/etc/systemd/system/` | root, 0644 | second sensor |
| `config/apertar-hardware-cam1.conf` | `/home/pi/` | pi, 0644 | second sensor |
| `scripts/apertar-boot-config` | `/usr/local/libexec/` | root, 0755 | Boot Config card |
| `config/apertar-boot-config.sudoers` | `/etc/sudoers.d/apertar-boot-config` | root, 0440 | Boot Config card |
| `scripts/apertar-media-trim` | `/usr/local/libexec/` | root, 0755 | drive trim |
| `config/apertar-media-trim.sudoers` | `/etc/sudoers.d/apertar-media-trim` | root, 0440 | drive trim |
| `config/apertar-media.tmpfiles.conf` | `/etc/tmpfiles.d/apertar-media.conf` | root, 0644 | runtime folder |
| `scripts/apertar-media-tune` | `/usr/local/libexec/` | root, 0755 | drive kernel tuning (optional) |
| `config/apertar-media.sudoers` | `/etc/sudoers.d/apertar-media` | root, 0440 | drive kernel tuning (optional) |
| `config/apertar-media-tune.conf` | `/home/pi/apertar-media-tune.conf` | pi, 0644 | write-path settings (optional) |
| `scripts/apertar-tune` | stays in the repo, run it from there | pi | edits the temporary tuning override |
| `config/apertar-core-capture-priority.conf` | `/etc/systemd/system/apertar-core.service.d/` | root, 0644 | real-time priority (optional) |

## 1. Start script (always, with the new Core)

```bash
install -m 0755 scripts/start-apertar-core.sh /home/pi/start-apertar-core.sh
```

Without `APERTAR_CAMERA` it starts Core exactly as 1.6.0.

## 2. Runtime folder (always)

```bash
sudo install -m 0644 config/apertar-media.tmpfiles.conf /etc/tmpfiles.d/apertar-media.conf
sudo systemd-tmpfiles --create
```

## 3. Boot Config card

```bash
sudo install -m 0755 -o root -g root scripts/apertar-boot-config /usr/local/libexec/apertar-boot-config
sudo install -m 0440 config/apertar-boot-config.sudoers /etc/sudoers.d/apertar-boot-config
sudo visudo -cf /etc/sudoers.d/apertar-boot-config
```

`visudo` must print "parsed OK".

## 4. Drive trim

```bash
sudo install -m 0755 -o root -g root scripts/apertar-media-trim /usr/local/libexec/apertar-media-trim
sudo install -m 0440 config/apertar-media-trim.sudoers /etc/sudoers.d/apertar-media-trim
sudo visudo -cf /etc/sudoers.d/apertar-media-trim
sudo -n /usr/local/libexec/apertar-media-trim /media/RAW
```

The last line must print "... trimmed" and ask no password.

## 5. Second sensor

```bash
[[ -f /home/pi/apertar-hardware-cam1.conf ]] || install -m 0644 config/apertar-hardware-cam1.conf /home/pi/apertar-hardware-cam1.conf
mkdir -p /home/pi/.config-cam1
sudo install -m 0644 config/apertar-core-cam1.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable apertar-core-cam1
```

Needs step 1 too. It runs only when two sensors are found.

## 6. Optional: write-path settings file

```bash
cp config/apertar-media-tune.conf /home/pi/apertar-media-tune.conf
```

No sudo. Core reads it at start and at each take.

## 7. Optional: drive kernel tuning

```bash
sudo install -m 0755 -o root -g root scripts/apertar-media-tune /usr/local/libexec/apertar-media-tune
sudo install -m 0440 config/apertar-media.sudoers /etc/sudoers.d/apertar-media
sudo visudo -cf /etc/sudoers.d/apertar-media
```

Used only with `kernel_tune = on` or `APERTAR_MEDIA_TUNE=1`.

## 8. Optional: real-time priority

```bash
sudo mkdir -p /etc/systemd/system/apertar-core.service.d
sudo install -m 0644 config/apertar-core-capture-priority.conf /etc/systemd/system/apertar-core.service.d/
sudo systemctl daemon-reload
```

It only raises the limits. It does something only with `APERTAR_RT=1` or `APERTAR_RT_CAPTURE_PRIORITY=N`.

## After any change

```bash
sudo systemctl restart apertar-core
```

More on each feature: `apertar-setup.zip`.
