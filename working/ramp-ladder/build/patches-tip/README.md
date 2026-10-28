# Partial rebase onto Patrik's GitHub tips (stopped 2026-10-28)

Stopped on purpose: Patrik is building T33 and T34 with Claude in VS Code. Reference only.

- `core/`: T31 speed ramping, T32 cap, T32 WebUI block, rebased onto Core `eb9cc39` (his "temp:" Clear HDR commits).
  The rebase guards his automatic Clear HDR switch at the top of `setFps` so it never runs in a take (it reconfigures).
- `ui/`: the two T32 UI patches rebased onto Apertar-UI `d8098d0`.
- Not rebased: T33 and T34. The finished, reviewed T33/T34 series is on the old base in `../patches-on-6ae70b5/`
  (Core `6ae70b5` + T31 + T32, UI `dc471c1` + T32).
