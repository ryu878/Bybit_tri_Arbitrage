"""Entry point for the dashboard service."""

import asyncio
from services.dashboard.main import run_dashboard


def main() -> None:
    asyncio.run(run_dashboard())


if __name__ == "__main__":
    main()
