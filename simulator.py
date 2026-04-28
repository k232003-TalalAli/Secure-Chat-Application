"""
This script exists only to simulate the working of the project by logging use of RSA,DES and Sha1
it documents the algorithm inputs and outputs in log.txt for last connection only.
"""

from __future__ import annotations
from pathlib import Path


LOG_PATH = Path(__file__).resolve().parent / "log.txt"
_ACTIVE = False


def _append(line: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as file_obj:
        file_obj.write(line + "\n")


def log(algorithm: str, mode: bool, data: list[str]) -> None:
    """
    algorithm: "sha1", "des", "rsa", "login", "msg"
    mode: False => login/encrypt/send, True => logout/decrypt/recv
    data: payload list, interpreted by algorithm type
    """
    global _ACTIVE

    algo = (algorithm or "").strip().lower()

    if algo == "login" and not mode:
        username = data[0] if data else "unknown"
        LOG_PATH.write_text("", encoding="utf-8")
        _ACTIVE = True
        _append(f"[{username}] Connected.")
        _append("")
        return

    if algo == "login" and mode:
        username = data[0] if data else "unknown"
        if _ACTIVE:
            _append("")
            _append(f"[{username}] Disconnected")
            _append("")
            _append("(end of log)")
        _ACTIVE = False
        return

    if not _ACTIVE:
        return

    if algo == "sha1":
        plain = data[0] if len(data) > 0 else ""
        sha_out = data[1] if len(data) > 1 else ""
        stored = data[2] if len(data) > 2 else ""
        _append(f"Sha1 used: {{{plain}}} -> {{{sha_out}}} == {{{stored}}}")
        _append("")
        return

    if algo == "des":
        left = data[0] if len(data) > 0 else ""
        right = data[1] if len(data) > 1 else ""
        if not mode:
            _append(f"Des encryption used: {{{left}}} -> {{{right}}}")
        else:
            _append(f"Des decryption used: {{{left}}} -> {{{right}}}")
        _append("")
        return

    if algo == "rsa":
        left = data[0] if len(data) > 0 else ""
        right = data[1] if len(data) > 1 else ""
        if not mode:
            _append(f"Rsa encryption used: {{{left}}} -> {{{right}}}")
        else:
            _append(f"Rsa decryption used: {{{left}}} -> {{{right}}} (rsa output)")
        _append("")
        return

    if algo == "msg":
        src = data[0] if len(data) > 0 else ""
        dst = data[1] if len(data) > 1 else ""
        payload = data[2] if len(data) > 2 else ""
        if not mode:
            _append(f"msg sent: {{from {src}, to {dst}, payload: {payload}}}")
        else:
            _append(f"msg received: {{from {src}, to {dst}, payload: {payload}}}")
        _append("")
