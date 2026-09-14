from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from easyrestore.backend.download import DownloadResult
from easyrestore.backend.identifier import resolve_product_type
from easyrestore.backend.ipsw_api import DeviceFirmwares, Firmware, IpswClient
from easyrestore.backend.ipsw_verify import VerifyResult
from easyrestore.backend.paths import default_ipsw_path, free_bytes
from easyrestore.session import FirmwareSource
from easyrestore.wizard.page import WizardPage
from easyrestore.wizard.workers import (
    DownloadWorker,
    FetchFirmwaresWorker,
    VerifyWorker,
    start_worker,
)


def _format_bytes(num: int | None) -> str:
    if num is None:
        return "?"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{num} B"


class FirmwarePage(WizardPage):
    title = "Choose firmware"
    subtitle = "Download a signed IPSW for this device, or use a file you already have."

    def __init__(self, session, parent=None) -> None:
        super().__init__(session, parent)
        self._client = IpswClient()
        self._firmwares: list[Firmware] = []
        self._busy = False
        self._thread = None
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        id_row = QHBoxLayout()
        id_row.addWidget(QLabel(self.tr("Device identifier")))
        self._identifier = QLineEdit()
        self._identifier.setPlaceholderText(self.tr("e.g. iPhone13,4"))
        self._identifier.setAccessibleName(self.tr("Device identifier"))
        self._identifier.editingFinished.connect(self._on_identifier_edited)
        id_row.addWidget(self._identifier, 1)
        self._lookup = QPushButton(self.tr("Look up"))
        self._lookup.setObjectName("Ghost")
        self._lookup.clicked.connect(self._start_lookup)
        id_row.addWidget(self._lookup)
        layout.addLayout(id_row)

        self._device_label = QLabel(self.tr("Enter a model identifier, or connect a device and look up."))
        self._device_label.setWordWrap(True)
        layout.addWidget(self._device_label)

        self._latest = QRadioButton(self.tr("Download the latest signed firmware"))
        self._choose = QRadioButton(self.tr("Choose a specific signed version"))
        self._local = QRadioButton(self.tr("Use an IPSW file already on this computer"))
        self._latest.setChecked(True)
        for radio in (self._latest, self._choose, self._local):
            radio.toggled.connect(self._sync_source)
            layout.addWidget(radio)

        self._version = QComboBox()
        self._version.setEnabled(False)
        self._version.setAccessibleName(self.tr("Signed firmware version"))
        self._version.currentIndexChanged.connect(self._on_version_changed)
        layout.addWidget(self._version)

        file_row = QHBoxLayout()
        self._path = QLineEdit()
        self._path.setPlaceholderText(self.tr("No file selected"))
        self._path.setReadOnly(True)
        self._path.setEnabled(False)
        self._browse = QPushButton(self.tr("Browse…"))
        self._browse.setObjectName("Ghost")
        self._browse.clicked.connect(self._browse_file)
        self._browse.setAccessibleName(self.tr("Browse for an IPSW file"))
        file_row.addWidget(self._path, 1)
        file_row.addWidget(self._browse)
        layout.addLayout(file_row)

        action_row = QHBoxLayout()
        self._action = QPushButton(self.tr("Download and verify"))
        self._action.setObjectName("Primary")
        self._action.clicked.connect(self._start_prepare)
        self._cancel = QPushButton(self.tr("Cancel"))
        self._cancel.setObjectName("Ghost")
        self._cancel.setEnabled(False)
        self._cancel.clicked.connect(self._cancel_work)
        action_row.addWidget(self._action)
        action_row.addWidget(self._cancel)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setAccessibleName(self.tr("Firmware download progress"))
        layout.addWidget(self._progress)

        self._status = QLabel(
            self.tr("Every IPSW is integrity-checked (zip CRC and SHA-1) before you can continue.")
        )
        self._status.setObjectName("Muted")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        layout.addStretch(1)

    def on_enter(self) -> None:
        identifier = self.session.device_identifier
        if not identifier and self.session.device and self.session.device.identifier:
            identifier = self.session.device.identifier
        if not identifier:
            identifier = resolve_product_type()
        if identifier:
            self._identifier.setText(identifier)
            self.session.device_identifier = identifier
            if self.session.device is not None and not self.session.device.identifier:
                # DeviceSnapshot is frozen — keep identifier on the session only.
                pass
            if not self._firmwares:
                self._start_lookup()
        self._refresh_action_label()
        self.can_continue_changed.emit(self.can_continue())

    def on_leave(self) -> bool:
        if self._busy:
            self._status.setText(self.tr("Wait for the download or verification to finish, or cancel it."))
            self._status.setObjectName("StatusWait")
            self._status.style().unpolish(self._status)
            self._status.style().polish(self._status)
            return False
        return True

    def can_continue(self) -> bool:
        return bool(self.session.ipsw_path and self.session.ipsw_verified and not self._busy)

    def _sync_source(self) -> None:
        if self._busy:
            return
        previous = self.session.firmware_source
        if self._latest.isChecked():
            source = FirmwareSource.LATEST_SIGNED
            if self._firmwares:
                self._version.setCurrentIndex(0)
        elif self._choose.isChecked():
            source = FirmwareSource.CHOOSE_VERSION
        else:
            source = FirmwareSource.LOCAL_FILE
        self.session.firmware_source = source
        choosing = source is FirmwareSource.CHOOSE_VERSION
        local = source is FirmwareSource.LOCAL_FILE
        self._version.setEnabled(choosing and bool(self._firmwares) and not self._busy)
        self._path.setEnabled(local and not self._busy)
        self._browse.setEnabled(local and not self._busy)
        if source is FirmwareSource.LOCAL_FILE:
            # Local files are checked for zip integrity only unless the user
            # explicitly matched them to a catalog entry later.
            self.session.expected_sha1 = None
        if source != previous:
            self.session.ipsw_verified = False
        self._refresh_action_label()
        self.can_continue_changed.emit(self.can_continue())

    def _update_control_enablement(self) -> None:
        choosing = self.session.firmware_source is FirmwareSource.CHOOSE_VERSION
        local = self.session.firmware_source is FirmwareSource.LOCAL_FILE
        self._version.setEnabled(choosing and bool(self._firmwares) and not self._busy)
        self._path.setEnabled(local and not self._busy)
        self._browse.setEnabled(local and not self._busy)

    def _on_identifier_edited(self) -> None:
        text = self._identifier.text().strip()
        self.session.device_identifier = text or None
        self.session.ipsw_verified = False
        self.can_continue_changed.emit(self.can_continue())

    def _on_version_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._firmwares):
            return
        self._apply_firmware(self._firmwares[index])
        if self._choose.isChecked():
            self.session.ipsw_verified = False
            self.can_continue_changed.emit(self.can_continue())

    def _apply_firmware(self, firmware: Firmware) -> None:
        self.session.selected_firmware = firmware
        self.session.selected_version = firmware.version
        self.session.selected_build = firmware.buildid
        if self.session.firmware_source is not FirmwareSource.LOCAL_FILE:
            self.session.expected_sha1 = firmware.sha1sum or None

    def _refresh_action_label(self) -> None:
        if self.session.firmware_source is FirmwareSource.LOCAL_FILE:
            self._action.setText(self.tr("Verify file"))
        else:
            self._action.setText(self.tr("Download and verify"))

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._lookup.setEnabled(not busy)
        self._action.setEnabled(not busy)
        self._cancel.setEnabled(busy)
        self._latest.setEnabled(not busy)
        self._choose.setEnabled(not busy)
        self._local.setEnabled(not busy)
        self._identifier.setEnabled(not busy)
        self._update_control_enablement()
        self.can_continue_changed.emit(self.can_continue())

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        self._thread = None
        self._worker = None
        pending = getattr(self, "_pending_verify", None)
        if pending:
            self._pending_verify = None
            path, sha1 = pending
            self._start_verify(path, sha1, already_busy=True)

    def _start_lookup(self) -> None:
        identifier = self._identifier.text().strip()
        if not identifier:
            self._device_label.setText(self.tr("Enter a device identifier like iPhone13,4."))
            return
        self.session.device_identifier = identifier
        self._set_busy(True)
        self._status.setText(self.tr("Looking up signed firmware on ipsw.me…"))
        self._status.setObjectName("Muted")
        self._progress.setRange(0, 0)

        worker = FetchFirmwaresWorker(self._client, identifier)
        thread = start_worker(worker)
        worker.finished.connect(self._on_lookup_finished)
        worker.failed.connect(self._on_lookup_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._cleanup_thread)
        self._worker = worker
        self._thread = thread
        thread.start()

    def _on_lookup_finished(self, device: DeviceFirmwares) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        signed = device.signed_firmwares()
        self._firmwares = signed
        self._version.blockSignals(True)
        self._version.clear()
        for fw in signed:
            label = self.tr("{version} ({build}) — {size}").format(
                version=fw.version,
                build=fw.buildid,
                size=_format_bytes(fw.filesize),
            )
            self._version.addItem(label)
        self._version.blockSignals(False)

        name = device.name or device.identifier
        if not signed:
            self._device_label.setText(
                self.tr("{name}: no signed firmware is available right now.").format(name=name)
            )
            self._status.setText(self.tr("Apple is not signing any firmware for this device."))
            self._set_busy(False)
            return

        self._device_label.setText(
            self.tr("{name}: {count} signed version(s) available.").format(
                name=name, count=len(signed)
            )
        )
        self._apply_firmware(signed[0])
        self._version.setCurrentIndex(0)
        self._status.setText(
            self.tr("Latest signed: {version} ({build}). Download and verify before continuing.").format(
                version=signed[0].version,
                build=signed[0].buildid,
            )
        )
        self._status.setObjectName("Muted")
        self._set_busy(False)

    def _on_lookup_failed(self, message: str) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._status.setText(self.tr("Lookup failed: {error}").format(error=message))
        self._status.setObjectName("StatusWait")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._set_busy(False)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select IPSW file"),
            str(Path.home()),
            self.tr("Apple firmware (*.ipsw);;All files (*)"),
        )
        if not path:
            return
        self.session.ipsw_path = Path(path)
        self.session.ipsw_verified = False
        self._path.setText(path)
        self._local.setChecked(True)
        self._status.setText(
            self.tr("Selected {name}. Click Verify file before continuing.").format(
                name=Path(path).name
            )
        )
        self._refresh_action_label()
        self.can_continue_changed.emit(self.can_continue())

    def _selected_firmware(self) -> Firmware | None:
        if self.session.firmware_source is FirmwareSource.LOCAL_FILE:
            return self.session.selected_firmware
        index = self._version.currentIndex()
        if 0 <= index < len(self._firmwares):
            return self._firmwares[index]
        return self.session.selected_firmware

    def _start_prepare(self) -> None:
        if self.session.firmware_source is FirmwareSource.LOCAL_FILE:
            path = self.session.ipsw_path
            if path is None:
                self._status.setText(self.tr("Choose an IPSW file first."))
                return
            # Zip/CRC only for arbitrary local files — do not require an ipsw.me SHA-1.
            self._start_verify(path, None)
            return

        firmware = self._selected_firmware()
        if firmware is None:
            self._status.setText(self.tr("Look up signed firmware for this device first."))
            return
        self._apply_firmware(firmware)

        needed = firmware.filesize or 0
        available = free_bytes()
        if needed and available < needed + (512 * 1024 * 1024):
            self._status.setText(
                self.tr(
                    "Not enough free space. Need about {need}, have {have}."
                ).format(need=_format_bytes(needed), have=_format_bytes(available))
            )
            self._status.setObjectName("StatusWait")
            self._status.style().unpolish(self._status)
            self._status.style().polish(self._status)
            return

        destination = default_ipsw_path(firmware.identifier, firmware.version, firmware.buildid)
        if destination.is_file() and destination.stat().st_size == firmware.filesize:
            self.session.ipsw_path = destination
            self._path.setText(str(destination))
            self._status.setText(self.tr("Found existing download. Verifying…"))
            self._start_verify(destination, firmware.sha1sum or None)
            return

        self._set_busy(True)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._status.setText(
            self.tr("Downloading {version} ({size})…").format(
                version=firmware.version,
                size=_format_bytes(firmware.filesize),
            )
        )
        worker = DownloadWorker(firmware, destination)
        thread = start_worker(worker)
        worker.progress.connect(self._on_download_progress)
        worker.finished.connect(self._on_download_finished)
        worker.failed.connect(self._on_work_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._cleanup_thread)
        self._worker = worker
        self._thread = thread
        thread.start()

    def _on_download_progress(self, done: int, total: object) -> None:
        total_int = total if isinstance(total, int) and total > 0 else None
        if total_int:
            self._progress.setValue(min(100, int(done * 100 / total_int)))
            self._status.setText(
                self.tr("Downloading… {done} / {total}").format(
                    done=_format_bytes(done),
                    total=_format_bytes(total_int),
                )
            )
        else:
            self._progress.setRange(0, 0)
            self._status.setText(
                self.tr("Downloading… {done}").format(done=_format_bytes(done))
            )

    def _on_download_finished(self, result: DownloadResult) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self.session.ipsw_path = result.path
        self._path.setText(str(result.path))
        note = self.tr("Resumed download.") if result.resumed else self.tr("Download complete.")
        self._status.setText(self.tr("{note} Verifying integrity…").format(note=note))
        firmware = self.session.selected_firmware
        sha1 = firmware.sha1sum if firmware else self.session.expected_sha1
        self._pending_verify = (result.path, sha1)

    def _start_verify(
        self, path: Path, expected_sha1: str | None, *, already_busy: bool = False
    ) -> None:
        if not already_busy:
            self._set_busy(True)
        self._progress.setRange(0, 0)
        self._status.setText(self.tr("Checking zip integrity and SHA-1…"))
        worker = VerifyWorker(path, expected_sha1)
        thread = start_worker(worker)
        worker.finished.connect(self._on_verify_finished)
        worker.failed.connect(self._on_work_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._cleanup_thread)
        self._worker = worker
        self._thread = thread
        thread.start()

    def _on_verify_finished(self, result: VerifyResult) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(100 if result.ok else 0)
        self.session.ipsw_verified = result.ok
        if result.ok:
            self._status.setText(result.message)
            self._status.setObjectName("StatusOk")
        else:
            self._status.setText(result.message)
            self._status.setObjectName("StatusWait")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._set_busy(False)

    def _on_work_failed(self, message: str) -> None:
        self._progress.setRange(0, 100)
        self.session.ipsw_verified = False
        self._status.setText(message)
        self._status.setObjectName("StatusWait")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        self._set_busy(False)

    def _cancel_work(self) -> None:
        worker = self._worker
        if isinstance(worker, DownloadWorker):
            worker.cancel()
            self._status.setText(self.tr("Cancelling download…"))
        else:
            self._status.setText(self.tr("Busy — wait for the current step to finish."))
