from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from easyrestore.backend.identifier import ensure_vendor_env
from easyrestore.helper.daemon import run_helper


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EasyRestore privileged helper")
    parser.add_argument(
        "--session",
        action="store_true",
        help="Use the session bus (development only; production uses the system bus).",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ensure_vendor_env()
    try:
        asyncio.run(run_helper(session_bus=args.session))
    except KeyboardInterrupt:
        return 0
    except Exception as exc:  # pragma: no cover - process entry
        print(f"easyrestore-helper: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
