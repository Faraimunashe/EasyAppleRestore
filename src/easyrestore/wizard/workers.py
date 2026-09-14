from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from easyrestore.backend.download import DownloadCancelled, DownloadError, download_file
from easyrestore.backend.http import HttpError
from easyrestore.backend.ipsw_api import DeviceFirmwares, Firmware, IpswClient
from easyrestore.backend.ipsw_verify import VerifyResult, verify_ipsw


class FetchFirmwaresWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, client: IpswClient, identifier: str) -> None:
        super().__init__()
        self._client = client
        self._identifier = identifier

    def run(self) -> None:
        try:
            device = self._client.fetch_device_firmwares(self._identifier)
        except (HttpError, ValueError, RuntimeError, OSError) as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(device)


class DownloadWorker(QObject):
    progress = Signal(int, object)  # bytes done, total or None
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, firmware: Firmware, destination: Path) -> None:
        super().__init__()
        self._firmware = firmware
        self._destination = destination
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            result = download_file(
                self._firmware.url,
                self._destination,
                expected_size=self._firmware.filesize or None,
                on_progress=lambda done, total: self.progress.emit(done, total),
                should_cancel=lambda: self._cancel,
            )
        except DownloadCancelled as exc:
            self.failed.emit(str(exc))
            return
        except DownloadError as exc:
            self.failed.emit(str(exc))
            return
        except OSError as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


class VerifyWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, path: Path, expected_sha1: str | None) -> None:
        super().__init__()
        self._path = path
        self._expected_sha1 = expected_sha1

    def run(self) -> None:
        try:
            result = verify_ipsw(self._path, self._expected_sha1)
        except OSError as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


def start_worker(worker: QObject, slot_name: str = "run") -> QThread:
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(getattr(worker, slot_name))
    return thread
