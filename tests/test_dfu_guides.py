from easyrestore.backend.dfu_guides import InputFamily, family_for_identifier, guide_for_identifier


def test_family_mapping_is_explicitly_unverified() -> None:
    assert family_for_identifier("iPhone13,4") is InputFamily.SIDE_VOLUME
    assert family_for_identifier("iPhone14,2") is InputFamily.SIDE_VOLUME
    assert family_for_identifier("iPhone14,6") is InputFamily.HOME_SIDE
    guide = guide_for_identifier("iPhone13,4")
    assert guide.verified is False
    assert guide.recovery
    assert guide.dfu
