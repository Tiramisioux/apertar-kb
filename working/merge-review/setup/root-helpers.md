# Root helpers

Core runs as `pi`. Three features need root. Each has a small script and a sudoers rule that allows exactly that script.

Without a helper the feature is off or falls back. Nothing breaks.

## Boot Config card (config.txt)

```bash
sudo install -m 0755 -o root -g root scripts/apertar-boot-config /usr/local/libexec/apertar-boot-config
sudo install -m 0440 config/apertar-boot-config.sudoers /etc/sudoers.d/apertar-boot-config
sudo visudo -cf /etc/sudoers.d/apertar-boot-config
```

Without it, Core uses `sudo -n install`, as the 1.6.0 fan mode does.

## Trim the recording drive

The NVMe stalls when it is not trimmed. Core trims after deletes and on mount.

```bash
sudo install -m 0755 -o root -g root scripts/apertar-media-trim /usr/local/libexec/apertar-media-trim
sudo install -m 0440 config/apertar-media-trim.sudoers /etc/sudoers.d/apertar-media-trim
sudo visudo -cf /etc/sudoers.d/apertar-media-trim
sudo -n /usr/local/libexec/apertar-media-trim /media/RAW   # must print "... trimmed" and ask no password
```

Turn off with `APERTAR_MEDIA_TRIM=0`.

## Kernel tuning of the recording drive (optional, off by default)

Only used with `APERTAR_MEDIA_TUNE=1` or `kernel_tune = on`.

```bash
sudo install -m 0755 -o root -g root scripts/apertar-media-tune /usr/local/libexec/apertar-media-tune
sudo install -m 0440 config/apertar-media.sudoers /etc/sudoers.d/apertar-media
```

## Runtime folder

Core and the automounter share state in `/run/apertar-media`.

```bash
sudo install -m 0644 config/apertar-media.tmpfiles.conf /etc/tmpfiles.d/apertar-media.conf
sudo systemd-tmpfiles --create
```
