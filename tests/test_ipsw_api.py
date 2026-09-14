from easyrestore.backend.ipsw_api import device_ipsws_url, firmware_url, parse_device_firmwares


def test_official_v4_urls() -> None:
    assert device_ipsws_url("iPhone13,4") == "https://api.ipsw.me/v4/ipsw/device/iPhone13%2C4"
    assert (
        firmware_url("iPhone13,4", "19H384")
        == "https://api.ipsw.me/v4/ipsw/iPhone13%2C4/19H384"
    )


def test_parse_device_firmwares_picks_first_signed() -> None:
    payload = {
        "identifier": "iPhone13,4",
        "name": "iPhone 12 Pro Max",
        "boards": [{"bdid": 1, "boardconfig": "d54ap", "cpid": 1, "platform": "t8101"}],
        "firmwares": [
            {
                "identifier": "iPhone13,4",
                "version": "17.0",
                "buildid": "21A329",
                "url": "https://example.test/old.ipsw",
                "filesize": 1,
                "sha1sum": "aaa",
                "signed": False,
            },
            {
                "identifier": "iPhone13,4",
                "version": "18.6.2",
                "buildid": "22G100",
                "url": "https://example.test/new.ipsw",
                "filesize": 2,
                "sha1sum": "bbb",
                "signed": True,
            },
        ],
    }
    device = parse_device_firmwares(payload)
    assert device.name == "iPhone 12 Pro Max"
    latest = device.latest_signed()
    assert latest is not None
    assert latest.version == "18.6.2"
    assert latest.sha1sum == "bbb"
