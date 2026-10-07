# -*- coding: utf-8 -*-
"""用 GetExtendedTcpTable 找出监听指定端口的 PID（纯 ctypes，无需管理员）。"""
import ctypes
import ctypes.wintypes as wt
import socket
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

AF_INET = 2
TCP_TABLE_OWNER_PID_LISTENER = 3


class MIB_TCPROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ("dwState", wt.DWORD),
        ("dwLocalAddr", wt.DWORD),
        ("dwLocalPort", wt.DWORD),
        ("dwRemoteAddr", wt.DWORD),
        ("dwRemotePort", wt.DWORD),
        ("dwOwningPid", wt.DWORD),
    ]


def listeners(ports):
    size = wt.DWORD(0)
    iphlpapi = ctypes.windll.iphlpapi
    ret = iphlpapi.GetExtendedTcpTable(None, ctypes.byref(size), False, AF_INET,
                                       TCP_TABLE_OWNER_PID_LISTENER, 0)
    buf = ctypes.create_string_buffer(size.value)
    ret = iphlpapi.GetExtendedTcpTable(buf, ctypes.byref(size), False, AF_INET,
                                       TCP_TABLE_OWNER_PID_LISTENER, 0)
    if ret != 0:
        print("GetExtendedTcpTable failed:", ret)
        return {}
    n = ctypes.cast(buf, ctypes.POINTER(wt.DWORD)).contents.value
    arr = ctypes.cast(ctypes.addressof(buf) + 4,
                      ctypes.POINTER(MIB_TCPROW_OWNER_PID * n)).contents
    out = {}
    for row in arr:
        port = socket.ntohs(row.dwLocalPort & 0xFFFF)
        if port in ports:
            out[port] = row.dwOwningPid
    return out


if __name__ == "__main__":
    print(listeners({8770, 5180}))
