#!/usr/bin/env python3
"""Drive a JupyterLab terminal over websocket using cookie auth (no token needed)."""
import sys
import json
import time
import urllib.request
import urllib.error
import websocket

HOST = "http://43.155.214.240:6888"
WS = "ws://43.155.214.240:6888"
COOKIE = ("username-43-155-214-240-6888=2|1:0|10:1784680378|28:username-43-155-214-240-6888|192:"
          "eyJ1c2VybmFtZSI6ICIzNzdkM2U2ZmNjMDY0MDBiOGUyNjRjM2JjODVmNTNmNSIsICJuYW1lIjogIkFub255bW91"
          "cyBUaGViZSIsICJkaXNwbGF5X25hbWUiOiAiQW5vbnltb3VzIFRoZWJlIiwgImluaXRpYWxzIjogIkFUIiwgImN"
          "vbG9yIjogbnVsbH0=|1a58b02dd74d740acc7b5427a2095db026313344cde987561ff5a1df9eff9db2; "
          "_xsrf=2|5e246ce4|66daf33cbd818687c10999c3b4f3c2eb|1784680378")
XSRF = "2|5e246ce4|66daf33cbd818687c10999c3b4f3c2eb|1784680378"


def create_terminal():
    req = urllib.request.Request(HOST + "/api/terminals", method="POST",
                                 data=b"", headers={"Cookie": COOKIE, "X-XSRFToken": XSRF})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def run(cmd, wait=4.0):
    info = create_terminal()
    name = info["name"]
    url = f"{WS}/terminals/websocket/{name}"
    ws = websocket.create_connection(url, header=[f"Cookie: {COOKIE}"], timeout=30)
    # set size (optional)
    ws.send(json.dumps(["set_size", 50, 160]))
    time.sleep(0.3)
    # clear any banner
    out = []
    ws.send(json.dumps(["stdin", cmd + "\n"]))
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            ws.settimeout(1.0)
            msg = ws.recv()
        except Exception:
            continue
        try:
            arr = json.loads(msg)
        except Exception:
            continue
        if arr and arr[0] in ("stdout", "stderr"):
            out.append(arr[1])
    ws.close()
    # cleanup terminal
    try:
        req = urllib.request.Request(HOST + f"/api/terminals/{name}", method="DELETE",
                                     headers={"Cookie": COOKIE, "X-XSRFToken": XSRF})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
    return "".join(out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "echo OK"
    wait = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    text = run(cmd, wait)
    print("=== OUTPUT ===")
    print(text)
