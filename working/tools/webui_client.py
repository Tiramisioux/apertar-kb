#!/usr/bin/env python3
"""webui_client.py - stand-in for the Apertar WebUI browser page, on the Mac.

Purpose
  A real browser's MJPEG <img> does not reconnect after Core closes the
  stream cleanly. During restart-heavy tests this client does what the page
  does continuously and reconnects by itself, so Core sees the same load.

Usage
  python3 -I webui_client.py [--host apertar.local] [--port 8000] [--log FILE]
  Stop with Ctrl-C or SIGTERM.

What it mirrors (Apertar-Core/src/web/WebControlPage.cpp)
  - fetchState(): `await fetch("/api/state", { cache: "no-store" })`, a plain
    GET with no body, called by `window.setInterval(() => fetchState(true), 1000)`.
    A new poll is skipped while one is in flight (state.fetchInFlight). A
    browser fetch reuses a keep-alive connection, so one persistent
    http.client connection is used here, reconnecting on failure. cache
    "no-store" makes the browser send Cache-Control: no-cache and Pragma:
    no-cache; the same headers are sent here.
  - loadPreviewStream()/installPreviewStream(): <img src="/preview.mjpeg?stream=N">
    with N incrementing per (re)connect; on error the page retries after
    1500 ms. Core side: streamMjpeg() in src/ApertarCoreApp.cpp.
  This client additionally reconnects after a clean EOF and after 5 s
  without data (the page does not).

Read-only
  It only ever sends GET /api/state and GET /preview.mjpeg. No POST, no
  /api/command, no other control endpoint. (The page's user_activity POST
  to /api/command is deliberately NOT mirrored.)

Log (every 10 s, stdout and --log FILE): local time, mjpeg connected
  yes/no, reconnects so far, MJPEG parts/s and KB/s over the last 10 s,
  state polls ok/fail in the last 10 s. Each reconnect is logged with reason.
"""
import argparse
import http.client
import signal
import socket
import sys
import threading
import time

STATE_PATH = "/api/state"
STATE_HEADERS = {"Cache-Control": "no-cache", "Pragma": "no-cache",
                 "Accept": "*/*", "User-Agent": "apertar-webui-client/1"}
SOCK_TIMEOUT = 10.0
IDLE_LIMIT = 5.0
RETRY_DELAY = 1.5
CHUNK = 64 * 1024

stop = threading.Event()
lock = threading.Lock()
stats = {"bytes": 0, "parts": 0, "ok": 0, "fail": 0,
         "connected": False, "reconnects": 0}
logfile = None


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    with lock:
        try:
            print(line, flush=True)
        except Exception:
            pass
        if logfile:
            try:
                logfile.write(line + "\n")
                logfile.flush()
            except Exception:
                pass


def mjpeg_thread(host, port):
    n = 0
    first = True
    while not stop.is_set():
        n += 1
        reason = None
        conn = None
        try:
            conn = http.client.HTTPConnection(host, port, timeout=SOCK_TIMEOUT)
            conn.request("GET", "/preview.mjpeg?stream=%d" % n,
                         headers={"Accept": "*/*", "User-Agent": "apertar-webui-client/1"})
            resp = conn.getresponse()
            if resp.status != 200:
                raise RuntimeError("HTTP %d" % resp.status)
            with lock:
                stats["connected"] = True
            if not first:
                log("mjpeg connected (stream=%d)" % n)
            first = False
            ctype = resp.getheader("Content-Type", "")
            boundary = b"--frame"
            if "boundary=" in ctype:
                b = ctype.split("boundary=", 1)[1].strip().strip('"')
                boundary = b if b.startswith("--") else "--" + b
                boundary = boundary.encode()
            tail = b""
            last_data = time.monotonic()
            sock = conn.sock
            while not stop.is_set():
                try:
                    data = resp.read1(CHUNK)
                except socket.timeout:
                    if time.monotonic() - last_data >= IDLE_LIMIT:
                        reason = "no data for %.0f s" % IDLE_LIMIT
                        break
                    continue
                if not data:
                    reason = "EOF (server closed stream)"
                    break
                last_data = time.monotonic()
                buf = tail + data
                cnt = buf.count(boundary)
                tail = buf[-(len(boundary) - 1):] if len(boundary) > 1 else b""
                # avoid double counting a boundary fully inside the kept tail
                if tail and boundary in tail:
                    tail = b""
                with lock:
                    stats["bytes"] += len(data)
                    stats["parts"] += cnt
                if time.monotonic() - last_data > IDLE_LIMIT:
                    reason = "no data"
                    break
        except Exception as e:
            reason = "error: %s: %s" % (type(e).__name__, e)
        finally:
            with lock:
                stats["connected"] = False
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        if stop.is_set():
            break
        with lock:
            stats["reconnects"] += 1
            rc = stats["reconnects"]
        log("mjpeg reconnect #%d after stream=%d: %s; waiting %.1f s" % (rc, n, reason, RETRY_DELAY))
        stop.wait(RETRY_DELAY)


def state_thread(host, port):
    conn = None
    nxt = time.monotonic()
    while not stop.is_set():
        try:
            if conn is None:
                conn = http.client.HTTPConnection(host, port, timeout=SOCK_TIMEOUT)
            conn.request("GET", STATE_PATH, headers=STATE_HEADERS)
            resp = conn.getresponse()
            resp.read()
            ok = 200 <= resp.status < 300
            if resp.will_close:
                conn.close()
                conn = None
        except Exception:
            ok = False
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
        with lock:
            stats["ok" if ok else "fail"] += 1
        nxt += 1.0
        now = time.monotonic()
        if nxt < now:  # a slow request skips ticks, like fetchInFlight
            nxt = now + (1.0 - ((now - nxt) % 1.0))
        stop.wait(max(0.0, nxt - now))


def main():
    global logfile
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="apertar.local")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--log")
    a = ap.parse_args()
    if a.log:
        logfile = open(a.log, "a", buffering=1)

    def handler(sig, frm):
        stop.set()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    log("start host=%s port=%d" % (a.host, a.port))
    for fn in (mjpeg_thread, state_thread):
        threading.Thread(target=fn, args=(a.host, a.port), daemon=True).start()

    last = dict(stats)
    while not stop.wait(10.0):
        with lock:
            s = dict(stats)
        log("mjpeg connected=%s reconnects=%d parts/s=%.1f KB/s=%.1f state ok=%d fail=%d" % (
            "yes" if s["connected"] else "no", s["reconnects"],
            (s["parts"] - last["parts"]) / 10.0,
            (s["bytes"] - last["bytes"]) / 1024.0 / 10.0,
            s["ok"] - last["ok"], s["fail"] - last["fail"]))
        last = s
    log("stopping")
    time.sleep(0.2)


if __name__ == "__main__":
    main()
