from pathlib import Path

from easyrestore.constants import DEVELOPER_EMAIL, DEVELOPER_MAILTO
from easyrestore.resources import resource_path

ROOT = Path(__file__).resolve().parents[1]


def test_developer_mailto() -> None:
    assert DEVELOPER_EMAIL == "faraimunashe.m11@gmail.com"
    assert DEVELOPER_MAILTO.startswith(f"mailto:{DEVELOPER_EMAIL}")
    assert "EasyRestore" in DEVELOPER_MAILTO


def test_bundled_logo_resources_exist() -> None:
    assert resource_path("easyrestore-logo.svg").is_file()
    assert resource_path("easyrestore-logo.png").is_file()


def test_hicolor_icon_set_installed_in_tree() -> None:
    svg = ROOT / "data/icons/io.easyrestore.EasyRestore.svg"
    assert svg.is_file()
    for size in (16, 24, 32, 48, 64, 128, 256, 512):
        png = (
            ROOT
            / "data/icons/hicolor"
            / f"{size}x{size}"
            / "apps"
            / "io.easyrestore.EasyRestore.png"
        )
        assert png.is_file(), str(png)
