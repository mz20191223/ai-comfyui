import os, json, urllib.request, sys

KEY = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DASHSCOPE_API_KEY", "")
PATH = sys.argv[2] if len(sys.argv) > 2 else "hedgehog_role_test.png"
FILES = "https://dashscope.aliyuncs.com/api/v1/files"

with open(PATH, "rb") as f:
    raw = f.read()
boundary = "----bailianclipboundary"
fn = os.path.basename(PATH)
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="{fn}"\r\n'
    f"Content-Type: image/png\r\n\r\n"
).encode("utf-8") + raw + f"\r\n--{boundary}--\r\n".encode("utf-8")
hdr = {"Authorization": f"Bearer {KEY}",
       "Content-Type": f"multipart/form-data; boundary={boundary}"}
req = urllib.request.Request(FILES, data=body, headers=hdr, method="POST")
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        print("HTTP", r.status)
        print(r.read().decode("utf-8", "replace"))
except urllib.error.HTTPError as e:
    print("HTTPError", e.code)
    print(e.read().decode("utf-8", "replace"))
