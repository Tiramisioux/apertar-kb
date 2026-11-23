# Services

## Second sensor (cam1)

Only for a camera with two sensors. File: `config/apertar-core-cam1.service`.

```bash
install -m 0755 scripts/start-apertar-core.sh /home/pi/start-apertar-core.sh
[[ -f /home/pi/apertar-hardware-cam1.conf ]] || install -m 0644 config/apertar-hardware-cam1.conf /home/pi/apertar-hardware-cam1.conf
mkdir -p /home/pi/.config-cam1
sudo install -m 0644 config/apertar-core-cam1.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable apertar-core-cam1
```

- It starts with `apertar-core.service`.
- It runs only when a sensor is on cam0 **and** on cam1. A check (`apertar-core --camera cam1 --check-dual`) decides this before start. With one sensor, systemd skips it. That is not an error.
- It uses its own socket (`/tmp/apertar-core-cam1.sock`), WebUI port 8001, settings folder `/home/pi/.config-cam1` and hardware file `/home/pi/apertar-hardware-cam1.conf`.
- Without that hardware file it does not start (exit 2, no restart loop).
- Remove: `sudo systemctl disable apertar-core-cam1`.

## Environment drop-in (for the switches)

Switches in [environment.md](environment.md) go in a drop-in for `apertar-core.service`:

```bash
sudo mkdir -p /etc/systemd/system/apertar-core.service.d
sudo nano /etc/systemd/system/apertar-core.service.d/apertar.conf
```

```ini
[Service]
Environment=APERTAR_SCRIPT_PATHS=ssh
```

Then `sudo systemctl daemon-reload && sudo systemctl restart apertar-core`.

## Real-time priority drop-in (optional)

Only for `APERTAR_RT=1` or `APERTAR_RT_CAPTURE_PRIORITY=N`. File: `config/apertar-core-capture-priority.conf`.

```bash
sudo install -m 0644 config/apertar-core-capture-priority.conf /etc/systemd/system/apertar-core.service.d/
sudo systemctl daemon-reload
```

It only raises the limits. On its own it changes nothing.
