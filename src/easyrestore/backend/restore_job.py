"""Long-lived restore job. Lives in the helper process so the GUI can reattach."""

from __future__ import annotations

import os
import shlex
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from easyrestore.backend.failures import explain_failure
from easyrestore.backend.identifier import vendor_bin
from easyrestore.backend.log_translate import RestorePhase, translate_log_line


class RestoreState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class RestoreStatus:
    job_id: str
    state: RestoreState
    phase: str
    percent: int
    message: str
    exit_code: int | None = None


@dataclass
class RestoreJob:
    job_id: str
    ipsw_path: Path
    erase: bool
    state: RestoreState = RestoreState.RUNNING
    phase: RestorePhase = RestorePhase.PREPARING
    percent: int = 0
    message: str = "Starting restore"
    exit_code: int | None = None
    log_lines: list[str] = field(default_factory=list)
    _process: subprocess.Popen[str] | None = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def status(self) -> RestoreStatus:
        with self._lock:
            return RestoreStatus(
                job_id=self.job_id,
                state=self.state,
                phase=self.phase.value,
                percent=self.percent,
                message=self.message,
                exit_code=self.exit_code,
            )

    def log_since(self, index: int) -> tuple[int, str]:
        with self._lock:
            chunk = self.log_lines[index:]
            return len(self.log_lines), "\n".join(chunk)

    def append_line(self, line: str) -> None:
        cleaned = line.rstrip("\n")
        translated = translate_log_line(cleaned)
        with self._lock:
            self.log_lines.append(cleaned)
            if translated.phase is not RestorePhase.UNKNOWN:
                self.phase = translated.phase
                self.message = translated.headline
            if translated.percent is not None:
                self.percent = translated.percent
            if translated.phase is RestorePhase.DONE:
                self.message = translated.headline

    def mark_finished(self, exit_code: int) -> None:
        with self._lock:
            self.exit_code = exit_code
            if exit_code == 0:
                self.state = RestoreState.SUCCEEDED
                self.phase = RestorePhase.DONE
                self.percent = 100
                self.message = "Restore finished"
            else:
                self.state = RestoreState.FAILED
                text = "\n".join(self.log_lines[-80:])
                explanation = explain_failure(text)
                if explanation:
                    self.message = f"{explanation.headline} {explanation.detail}"
                else:
                    self.message = f"Restore failed (exit {exit_code})"


def build_idevicerestore_command(
    ipsw_path: Path,
    *,
    erase: bool,
    binary: Path | None = None,
) -> list[str]:
    tool = binary or vendor_bin("idevicerestore")
    if tool is None:
        raise FileNotFoundError(
            "idevicerestore not found. Build the vendor stack or install it on PATH."
        )
    cmd = [str(tool), "-y"]
    if erase:
        cmd.append("-e")
    cmd.append(str(ipsw_path))
    return cmd


def _stub_script(ipsw_path: Path, erase: bool) -> str:
    mode = "erase" if erase else "update"
    return f"""#!/bin/sh
echo "Extracting IPSW {shlex.quote(str(ipsw_path))}"
echo "Personalizing firmware for {mode}"
echo "Sending iBEC"
echo "Sending SystemVolume"
echo "Verifying restore (40)"
echo "Creating system key bag (70)"
echo "Waiting for device to reconnect"
echo "Restore Successful"
exit 0
"""


class RestoreManager:
    """At most one restore at a time. Survives GUI disconnects."""

    def __init__(self) -> None:
        self._job: RestoreJob | None = None
        self._lock = threading.Lock()

    @property
    def current(self) -> RestoreJob | None:
        with self._lock:
            return self._job

    def reset_for_tests(self) -> None:
        with self._lock:
            job = self._job
            self._job = None
        if job and job._process and job._process.poll() is None:
            job._process.kill()
            try:
                job._process.wait(timeout=2)
            except Exception:
                pass

    def start(self, ipsw_path: Path, *, erase: bool) -> RestoreJob:
        path = Path(ipsw_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"IPSW not found: {path}")
        if path.suffix.lower() != ".ipsw":
            raise ValueError("Firmware path must be an .ipsw file")

        with self._lock:
            if self._job and self._job.state is RestoreState.RUNNING:
                raise RuntimeError("A restore is already running")
            job = RestoreJob(job_id=str(uuid.uuid4()), ipsw_path=path, erase=erase)
            self._job = job

        thread = threading.Thread(target=self._run, args=(job,), daemon=True)
        thread.start()
        return job

    def _run(self, job: RestoreJob) -> None:
        from easyrestore.backend.identifier import ensure_vendor_env, vendor_prefix

        ensure_vendor_env()
        env = os.environ.copy()
        prefix = vendor_prefix()
        if prefix is not None:
            env["EASYRESTORE_VENDOR_PREFIX"] = str(prefix)
            env["PATH"] = f"{prefix}/bin:{prefix}/sbin:" + env.get("PATH", "")
            env["LD_LIBRARY_PATH"] = (
                f"{prefix}/lib:{prefix}/lib64:" + env.get("LD_LIBRARY_PATH", "")
            )

        try:
            if os.environ.get("EASYRESTORE_RESTORE_STUB") == "1":
                script = _stub_script(job.ipsw_path, job.erase)
                process = subprocess.Popen(  # noqa: S603
                    ["/bin/sh", "-s"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                    bufsize=1,
                )
                assert process.stdin is not None
                process.stdin.write(script)
                process.stdin.close()
            else:
                cmd = build_idevicerestore_command(job.ipsw_path, erase=job.erase)
                job.append_line("Running: " + " ".join(shlex.quote(part) for part in cmd))
                process = subprocess.Popen(  # noqa: S603
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                    bufsize=1,
                )
        except Exception as exc:  # noqa: BLE001 — surface any spawn failure
            job.append_line(f"Failed to start restore: {exc}")
            job.mark_finished(1)
            return

        job._process = process
        assert process.stdout is not None
        for line in process.stdout:
            job.append_line(line)
        exit_code = process.wait()
        # Tiny pause so late buffered lines are unlikely; stdout iteration already drained.
        time.sleep(0.05)
        job.mark_finished(exit_code)


MANAGER = RestoreManager()
