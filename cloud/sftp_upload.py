import paramiko, os, sys

def main():
    host, port, user = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    local, remote = sys.argv[4], sys.argv[5]
    pw = os.environ.get("SSH_PASS")
    if not pw:
        sys.exit("ERROR: SSH_PASS env not set")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, user, password=pw, timeout=120)
    sftp = ssh.open_sftp()
    # ensure remote dir exists (recursive mkdir)
    rdir = os.path.dirname(remote)
    if rdir:
        cur = ""
        for p in rdir.strip("/").split("/"):
            cur = cur + "/" + p if cur else "/" + p
            try:
                sftp.stat(cur)
            except IOError:
                try:
                    sftp.mkdir(cur)
                except IOError:
                    pass
    print(f"put {local} -> {remote} ({os.path.getsize(local)} bytes)")
    sftp.put(local, remote)
    sftp.close()
    ssh.close()
    print("UPLOADED_OK", remote)

if __name__ == "__main__":
    main()
