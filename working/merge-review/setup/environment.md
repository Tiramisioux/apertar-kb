# Environment switches

Set them in the drop-in from [services.md](services.md). Unset means the default.

## Security (read these first)

| Switch | Effect |
| --- | --- |
| `APERTAR_SCRIPT_PATHS=ssh` | The WebUI cannot set a new `run_script` path. Paths are set over ssh only. Unset = as 1.6.0. |
| `APERTAR_BOOT_CONFIG_TEXT=on` | The Boot Config card can edit all of `config.txt` as text. Anyone on the WebUI can then write it as root. Default off. |

## Features

| Switch | Default | Effect |
| --- | --- | --- |
| `APERTAR_FPS_LIMIT=table` or `probe` | see note | `table`: the lower of Core's table and the sensor probe. `probe`: the probe alone. Today the default is `probe`. Dynamic resolution makes `table` the default, as in fork main. |
| `APERTAR_STORAGE_PREROLL=1` or `0` | off | storage pre-roll at start and on card insert. Wins over `[media] preroll`. |
| `APERTAR_MEDIA_TRIM=0` | on | no trim of the recording drive |
| `APERTAR_CLIP_MERGE=0` | on | split clips stay split |
| `APERTAR_CDNG_FRAMES_PER_FOLDER=N` | 0 | clip split, wins over the hardware file |
| `APERTAR_PIPELINE_CONFIG=/full/path.yaml` | none | libcamera pipeline config (see [boot-and-tuning.md](boot-and-tuning.md)) |
| `APERTAR_CAMERA`, `APERTAR_WEB_PORT` | cam0, 8000 | set by the cam1 unit, not by hand |

## Test knobs

Many more `APERTAR_*` variables exist for A/B tests of the write path (buffers, writers, sync, real-time priority). Each restores an older behaviour or turns on a measured option. They are listed in the Core `README.md`, section "Write-path knobs for A/B tests". A normal camera sets none of them.
