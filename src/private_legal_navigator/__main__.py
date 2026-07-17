"""Entry point for running PrivateLegalNavigator via `python -m private_legal_navigator`."""

import uvicorn

from private_legal_navigator.config import Settings


def main() -> None:
    """Start the FastAPI server on localhost."""
    settings = Settings()
    uvicorn.run(
        "private_legal_navigator.app:create_app",
        host=settings.host,
        port=settings.port,
        factory=True,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
