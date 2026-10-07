p = r"D:\Aicomfyui\短剧工作台\backend\app\services\script_service.py"
raw = open(p, "rb").read()
has_crlf = b"\r\n" in raw
lines = raw.decode("utf-8").split("\n")
before = len(lines)
lines = [l for l in lines if l.strip() != "project_id, rows, unmatched)"]
after = len(lines)
assert before - after == 1, (before, after)
open(p, "wb").write(("\r\n" if has_crlf else "\n").join(lines).encode("utf-8"))
print("removed residual line: %d -> %d" % (before, after))
