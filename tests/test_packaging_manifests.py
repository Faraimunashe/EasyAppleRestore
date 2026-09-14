from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_packaging_manifests_exist() -> None:
    expected = [
        "packaging/flatpak/io.easyrestore.EasyRestore.yml",
        "packaging/snap/snapcraft.yaml",
        "packaging/debian/control",
        "packaging/debian/rules",
        "packaging/debian/changelog",
        "packaging/APPIMAGE.md",
        "packaging/README.md",
        "data/udev/39-easyrestore.rules",
    ]
    for rel in expected:
        path = ROOT / rel
        assert path.is_file(), rel


def test_flatpak_declares_device_all_and_helper_talk() -> None:
    text = (ROOT / "packaging/flatpak/io.easyrestore.EasyRestore.yml").read_text(
        encoding="utf-8"
    )
    assert "--device=all" in text
    assert "--system-talk-name=io.easyrestore.Helper" in text
    assert "org.freedesktop.PolicyKit1" in text


def test_snap_requests_raw_usb() -> None:
    text = (ROOT / "packaging/snap/snapcraft.yaml").read_text(encoding="utf-8")
    assert "raw-usb" in text
    assert "confinement: strict" in text


def test_udev_rule_targets_apple_vid() -> None:
    text = (ROOT / "data/udev/39-easyrestore.rules").read_text(encoding="utf-8")
    assert 'ATTR{idVendor}=="05ac"' in text
    assert "uaccess" in text


def test_debian_splits_gui_and_helper() -> None:
    text = (ROOT / "packaging/debian/control").read_text(encoding="utf-8")
    assert "Package: easyrestore\n" in text
    assert "Package: easyrestore-helper\n" in text
