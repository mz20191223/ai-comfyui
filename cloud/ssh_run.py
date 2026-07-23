#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 SSH 在 HAI 实例内执行命令（参数来自环境变量 SSH_PASS，避免密码进命令行）。

用法（在 Bash 里）：
  set SSH_PASS=密码
  python ssh_run.py --host 43.155.213.145 --port 22 --user root --cmd "命令"

支持多行命令；默认超时 180s。返回 stdout/stderr。
"""
import os
import argparse
import paramiko


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=22)
    ap.add_argument("--user", default="root")
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    pw = os.environ.get("SSH_PASS")
    if not pw:
        print("ERROR: 环境变量 SSH_PASS 未设置")
        raise SystemExit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(args.host, port=args.port, username=args.user,
                       password=pw, timeout=30, banner_timeout=30)
    except Exception as e:
        print("SSH 连接失败:", repr(e))
        raise SystemExit(2)

    stdin, stdout, stderr = client.exec_command(args.cmd, timeout=args.timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print("=== STDOUT ===")
    print(out)
    if err.strip():
        print("=== STDERR ===")
        print(err)
    client.close()


if __name__ == "__main__":
    main()
