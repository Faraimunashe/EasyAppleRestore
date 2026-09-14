"""Application identifiers shared by the GUI, helper, and install files."""

from __future__ import annotations

APP_NAME = "EasyRestore"
APP_ID = "io.easyrestore.EasyRestore"
DEVELOPER_EMAIL = "faraimunashe.m11@gmail.com"
DEVELOPER_MAILTO = (
    f"mailto:{DEVELOPER_EMAIL}"
    "?subject=EasyRestore%20support"
)
HELPER_BUS_NAME = "io.easyrestore.Helper"
HELPER_OBJECT_PATH = "/io/easyrestore/Helper"
HELPER_INTERFACE = "io.easyrestore.Helper"
POLKIT_ACTION_GET_DEVICE_MODE = "io.easyrestore.Helper.getdevicemode"
POLKIT_ACTION_START_RESTORE = "io.easyrestore.Helper.startrestore"
POLKIT_ACTION_RUN_PREFLIGHT = "io.easyrestore.Helper.runpreflight"

APPLE_VENDOR_ID = 0x05AC

# Product IDs from libirecovery (enum irecv_mode).
IRECV_RECOVERY_PIDS = frozenset({0x1280, 0x1281, 0x1282, 0x1283})
IRECV_DFU_PID = 0x1227
IRECV_WTF_PID = 0x1222
IRECV_PORT_DFU_PID = 0xF014

# Common usbmux / normal-mode PIDs. Anything else under Apple VID that is not
# recovery/DFU is treated as normal unless a later lockdown probe says otherwise.
NORMAL_MODE_PIDS = frozenset(
    {
        0x1290,
        0x1292,
        0x1294,
        0x1297,
        0x129A,
        0x129C,
        0x129E,
        0x12A0,
        0x12A8,
        0x12AB,
    }
)

IPSW_API_BASE = "https://api.ipsw.me/v4"
IPSW_API_USER_AGENT = f"{APP_NAME}/{__import__('easyrestore').__version__} (+https://ipsw.me/api/)"
