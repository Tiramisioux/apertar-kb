---
datum: 2026-10-25 20:34:50
kontext: CINEMATE
projekt: "#APERTAR"
fritext: manual-addendum-talk-to-core
typ: digital anteckning
---

# Manual addendum: talking to Core from the Mac

For the Apertar manual (`20261025180000 CINEMATE APERTAR manual`). Suggested place: a new section after 4 (Building and deploying), or a new 4.6. Found 2026-10-25 while testing the `set_clear_hdr` command (tutorial T16, Step 2).

## The trap

`127.0.0.1` is always the machine you type on. A `curl` to `http://127.0.0.1:8000` typed **on the Mac** goes to the Mac, finds nothing and, with `-s`, prints **nothing at all**: no error, no HTTP code. It looks like Core ignored the command. Use the Pi's name from the Mac.

| Typed on | Address |
| --- | --- |
| the Pi (terminal in VS Code Remote) | `http://127.0.0.1:8000` |
| the Mac | `http://apertar.local:8000` (or the Pi's IP if mDNS fails) |

Core listens on all interfaces (`web control available on http://0.0.0.0:8000` in the journal), so both work.

## Read a value (changes nothing)

```bash
curl -s -m 5 http://apertar.local:8000/api/state | grep -o '"clear_hdr":[a-z]*'
```

## Send a command (changes something)

```bash
curl -s -m 10 -w '\nhttp=%{http_code}\n' -X POST http://apertar.local:8000/api/command \
  -d '{"cmd":"set_clear_hdr","enabled":"true"}'
```

- `-m 10`: a camera restart takes a few seconds; without it curl may give up early.
- `-w '\nhttp=%{http_code}\n'`: prints the HTTP code after the body. An empty reply with no `http=` line, or `http=000`, means the request never reached Core.
- Values are strings (`"true"`, `"1"`): the socket parser is flat.
- Drop the trailing `| grep` while debugging. It hides error replies.

## Is the command wired up? (changes nothing)

Leave out the argument. A wired handler answers with its own error text:

```bash
curl -s -m 5 -X POST http://apertar.local:8000/api/command -d '{"cmd":"set_clear_hdr"}'
# {"ok":false,"error":"set_clear_hdr requires enabled."}
```

An unknown name answers `Unknown command: <name>`.

## Where else to look

| Place | How |
| --- | --- |
| Persisted value | on the Pi: `grep clear_hdr ~/.config/apertar-core/camera_settings.conf` |
| Did the camera restart? | on the Pi: `journalctl -u apertar-core --since "-2min" \| grep "camera configured"` |
| Did the whole service restart? | `ps -o pid=,lstart= -C apertar-core`: a new pid or start time means yes |

A clean `systemctl restart` in the journal reads `Deactivated successfully`, then `Started`. A crash reads `code=killed` or `Failed with result`.

#CINEMATE
#APERTAR
