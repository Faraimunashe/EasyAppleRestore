from pathlib import Path

import tomllib

LOCK = Path(__file__).resolve().parents[1] / "vendor" / "versions.lock"


def test_lockfile_pins_exact_commits() -> None:
    data = tomllib.loads(LOCK.read_text(encoding="utf-8"))
    names = [item["name"] for item in data["components"]]
    assert names == [
        "libplist",
        "libimobiledevice-glue",
        "libusbmuxd",
        "libtatsu",
        "libimobiledevice",
        "libirecovery",
        "usbmuxd",
        "idevicerestore",
    ]
    for item in data["components"]:
        assert len(item["commit"]) == 40
        assert item["commit"].isalnum()
        assert "master" not in item["commit"]
        assert "latest" not in item["url"]

    by_name = {item["name"]: item for item in data["components"]}
    assert by_name["idevicerestore"]["commit"] == data["asr_timeout_commit"]
    assert by_name["idevicerestore"]["commit"].startswith("405fcd1")
    assert "--without-limera1n" in by_name["idevicerestore"]["extra_configure"]
