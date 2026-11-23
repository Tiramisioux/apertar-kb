# Lanes: work in flight, saved as patches

Each folder holds the commits a worker lane has made that are **not yet on the improvement branch**
(`claude/awesome-pasteur-qzsiow`). They are saved here so that nothing is lost if the review container goes away.
A patch here has passed its own gate and, usually, a second worker's review. It has not yet been read by the lead,
checked against the owner's recorded decisions, or gated together with the other lanes. So it may still change or
be dropped. When a lane is integrated, its folder is emptied.

| Folder | Repo | Base commit | What |
| --- | --- | --- | --- |
| `core-bugs/` | Apertar-Core | `0d13a6f` | Confirmed bugs (playback handle leak, clip-name probing under the camera lock, write-queue stop, audio writer, step lists, hardware store) |
| `core-command-plane/` | Apertar-Core | `56e135c` | Commits of `design/command-plane.md` |
| `core-hardware-inputs/` | Apertar-Core | `56e135c` | Commits of `design/hardware-inputs.md` |
| `core-camera-modes/` | Apertar-Core | `56e135c` | Commits of `design/camera-modes.md` |
| `ui-touch-ui/` | Apertar-UI | `ac1fc28` | Commits of `design/touch-ui.md` |

To look at one: open the `.patch` file (it is a commit with its message). To try a lane on a checkout of the base
commit: `git am <folder>/*.patch`.
