from __future__ import annotations

import uvicorn

from .settings import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run("book_series_grapher.api:create_app", factory=True, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
