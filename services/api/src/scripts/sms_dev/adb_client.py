"""ADB device detection + SMS retrieval (spec Part 16).

Two retrieval paths:
  1. `content query` directly over ADB shell - fast, no app install needed,
     but restricted/empty on many OEM ROMs (MIUI, OneUI, etc. often block
     shell-level SMS content-provider reads).
  2. The debug-only exporter broadcast receiver
     (apps/mobile/android/app/src/debug/.../SmsExportReceiver.kt) - requires
     a debug build of the app installed on the device, but works wherever
     the app itself is allowed to read SMS.

`pull_sms()` tries (1) first and automatically falls through to (2) when it
comes back empty, per the plan (`content query` is the fast path, the debug
helper is the reliable fallback).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

_APP_PACKAGE = "com.ledgerapp.mobile"
_EXPORT_ACTION = "com.ledgerapp.mobile.dev.EXPORT_SMS"
_EXPORT_REMOTE_PATH = f"/sdcard/Android/data/{_APP_PACKAGE}/files/sms_export.json"

_COMMON_ADB_PATHS = [
    Path.home() / "Android/Sdk/platform-tools/adb",
    Path("/usr/bin/adb"),
    Path("/usr/local/bin/adb"),
]


class AdbError(RuntimeError):
    pass


@dataclass
class Device:
    serial: str
    state: str
    model: str | None = None


def find_adb_binary() -> str:
    which = shutil.which("adb")
    if which:
        return which
    for candidate in _COMMON_ADB_PATHS:
        if candidate.exists():
            return str(candidate)
    raise AdbError(
        "adb not found on PATH or in common Android SDK locations. "
        "Install Android platform-tools or add it to PATH."
    )


def _run(adb: str, *args: str, timeout: int = 30) -> str:
    result = subprocess.run([adb, *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise AdbError(f"adb {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def list_devices(adb: str | None = None) -> list[Device]:
    adb = adb or find_adb_binary()
    output = _run(adb, "devices", "-l")
    devices = []
    for line in output.splitlines()[1:]:  # first line is "List of devices attached"
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        serial, state = parts[0], parts[1]
        model = next((p.split(":", 1)[1] for p in parts[2:] if p.startswith("model:")), None)
        devices.append(Device(serial=serial, state=state, model=model))
    return devices


def ensure_device_accessible(serial: str | None = None, adb: str | None = None) -> Device:
    adb = adb or find_adb_binary()
    devices = list_devices(adb)
    if not devices:
        raise AdbError("no Android device/emulator detected - connect your phone (with USB debugging enabled) and retry.")

    if serial:
        matches = [d for d in devices if d.serial == serial]
        if not matches:
            raise AdbError(f"no device with serial {serial!r} found. Connected: {[d.serial for d in devices]}")
        device = matches[0]
    else:
        if len(devices) > 1:
            raise AdbError(f"multiple devices connected ({[d.serial for d in devices]}) - pass --serial to pick one.")
        device = devices[0]

    if device.state != "device":
        raise AdbError(
            f"device {device.serial} is in state {device.state!r}, not ready "
            "(common causes: unauthorized - check the phone screen for a USB debugging prompt; offline - reconnect the cable)."
        )
    return device


# Splits the whole `content query` output into one chunk per row, at each
# "Row: <N> " marker - NOT per newline. A naive line-by-line parse silently
# truncates any SMS body containing an embedded newline (multi-line bank
# templates are common - "Received!\nINR 100 in HDFC Bank A/c..." - and
# would otherwise parse as just "Received!" with everything else dropped,
# a real data-loss bug found via LED-18's own real-device QA pass).
_ROW_SPLIT_RE = re.compile(r"(?=^Row: \d+ )", re.MULTILINE)
# `body` is always the LAST field in the fixed projection order requested
# by pull_sms_content_query ("_id:address:date:thread_id:sub_id:body"), so
# everything after "body=" up to the next row boundary is the literal body
# - including embedded commas/newlines that would otherwise break a
# field-by-field comma-split parse.
_ROW_HEADER_RE = re.compile(
    r"^Row:\s*\d+\s+_id=(?P<_id>[^,]*),\s*address=(?P<address>[^,]*),\s*date=(?P<date>[^,]*),\s*"
    r"thread_id=(?P<thread_id>[^,]*),\s*sub_id=(?P<sub_id>[^,]*),\s*body=(?P<body>.*)",
    re.DOTALL,
)


def _parse_content_query_output(raw: str) -> list[dict]:
    """`adb shell content query` prints one `Row: N field=value, field=value`
    block per row (not JSON) - see _ROW_SPLIT_RE/_ROW_HEADER_RE above for
    why this can't be a simple per-line or per-comma split."""
    rows = []
    for chunk in _ROW_SPLIT_RE.split(raw):
        chunk = chunk.strip("\n")
        if not chunk.startswith("Row:"):
            continue
        match = _ROW_HEADER_RE.match(chunk)
        if not match:
            continue
        row = match.groupdict()
        row["body"] = row["body"].rstrip("\n")
        rows.append(row)
    return rows


def pull_sms_content_query(device: Device, adb: str | None = None) -> list[dict]:
    adb = adb or find_adb_binary()
    try:
        raw = _run(
            adb,
            "-s",
            device.serial,
            "shell",
            "content",
            "query",
            "--uri",
            "content://sms/",
            "--projection",
            "_id:address:date:thread_id:sub_id:body",
            timeout=60,
        )
    except AdbError:
        return []
    return _parse_content_query_output(raw)


def trigger_debug_exporter(device: Device, adb: str | None = None) -> None:
    adb = adb or find_adb_binary()
    _run(
        adb,
        "-s",
        device.serial,
        "shell",
        "am",
        "broadcast",
        "-a",
        _EXPORT_ACTION,
        "-n",
        f"{_APP_PACKAGE}/.sms.SmsExportReceiver",
    )


def pull_sms_debug_helper(device: Device, adb: str | None = None) -> list[dict]:
    """Triggers the debug-only exporter (requires a debug build of the app
    installed on the device) then `adb pull`s its JSON output."""
    adb = adb or find_adb_binary()
    trigger_debug_exporter(device, adb)

    with tempfile.TemporaryDirectory() as tmp:
        local_path = Path(tmp) / "sms_export.json"
        try:
            _run(adb, "-s", device.serial, "pull", _EXPORT_REMOTE_PATH, str(local_path), timeout=60)
        except AdbError as e:
            raise AdbError(
                "could not pull the debug exporter's output - is a *debug* build of the "
                "app installed on the device? (release builds never include this exporter)"
            ) from e
        return json.loads(local_path.read_text())


def pull_sms(device: Device, adb: str | None = None) -> tuple[list[dict], str]:
    """Returns (messages, method_used)."""
    rows = pull_sms_content_query(device, adb)
    if rows:
        return rows, "content_query"

    messages = pull_sms_debug_helper(device, adb)
    return messages, "debug_helper"
