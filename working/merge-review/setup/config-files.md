# Config files

Old files keep working. A missing section means the feature is off. Core writes a full template to `~/apertar-hardware.conf` only when no hardware file exists. It never overwrites a file.

## apertar-hardware.conf: new sections

| Section | What | Default |
| --- | --- | --- |
| `[gpio_buttons]` | buttons on Pi GPIO pins. The 1.6.0 name `[gpio]` is still read. | off |
| `[gpio_encoders]` | rotary encoders on GPIO | off |
| `[gpio_switches]` | 2- and 3-way switches on GPIO | off |
| `[grove_analog]` | Grove analog knobs | off |
| `[neorotary4]` | NeoRotary 4 encoder board (I2C) | off |
| `[mpu6050]` `[bmi160]` `[bmi270]` `[icm42688p]` | IMU chips. Pick one with `[imu] driver=`. | as `[imu]` |
| `[camera]` | highest ISO in Clear HDR, per bit depth | no cap |
| `[media]` | storage pre-roll (`preroll=on`, `preroll_seconds`) | off |
| `[network]` | hotspot fallback delay | 60 s |
| `[storage]` | new keys: `buffer`, `split`, `frames_per_folder`, `clip_merge` | see below |

Buttons that are normally closed: set `invert_on_start=true` in `[gpio_buttons]` or `[pcf8574]`.

### [storage] keys

- `buffer=frames` (default) is the 1.6.0 queue. `buffer=ram` is a large RAM queue.
- `split=on` (default), `off` or `auto` splits a take into `part_NNN` folders. `auto` splits only above 32 fps for cDNG and lossy DNG on exFAT. On by default changes a stock 1.6.0 camera; the owner chose it.
- `frames_per_folder=N` is the part size (default 5000). An old file with `frames_per_folder=0` means split off.
- `clip_merge=on` (default) flattens split clips while the camera is idle, so Resolve sees one folder per clip.

## apertar-hardware-cam1.conf

Only for a second sensor. Template: `config/apertar-hardware-cam1.conf`. It turns every input off, so the two Cores never both read the buttons.

## ~/apertar-media-tune.conf (optional)

Write-path settings per drive type and filesystem, without a systemd drop-in. Copy the template, no sudo:

```bash
cp config/apertar-media-tune.conf ~/apertar-media-tune.conf
```

An environment variable wins over the file. `scripts/apertar-tune` writes a temporary override in RAM, which is gone at reboot.

## Files Core writes by itself

You install none of these.

- `~/.config/apertar-core/camera_settings.conf` gains keys such as `preview_tdn` and `stop_on_dropped_frame`. A 1.6.0 file loads. Missing keys take the 1.6.0 behaviour.
- Dynamic resolution keeps its keys in `camera_settings.conf` (`dynres_enabled`, `dynres_modes`, `dynres_aspects`, `dynres_tdn`). An old `mode_ladder.conf` is read once and taken over.
