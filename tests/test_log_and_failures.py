from easyrestore.backend.failures import explain_failure
from easyrestore.backend.log_translate import RestorePhase, translate_log_line


def test_translate_known_restore_lines() -> None:
    sending = translate_log_line("Sending SystemVolume")
    assert sending.phase is RestorePhase.COPYING
    verify = translate_log_line("Verifying restore (14)")
    assert verify.phase is RestorePhase.VERIFYING
    assert verify.percent == 14
    keybag = translate_log_line("Creating system key bag (50)")
    assert keybag.phase is RestorePhase.FINALIZING
    assert keybag.percent == 50


def test_known_failure_signatures() -> None:
    usb = explain_failure("ERROR: Unable to discover device type")
    assert usb is not None
    assert "USB" in usb.detail or "cable" in usb.detail.lower()
    asr = explain_failure("Unable to send data to ASR")
    assert asr is not None
    assert asr.key == "asr_transfer"
    restart = explain_failure("Could not read data (-256)")
    assert restart is not None
    assert "restarting" in restart.headline.lower()
    assert explain_failure("some unrelated warning") is None
