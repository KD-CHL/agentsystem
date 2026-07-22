from __future__ import annotations

import os

import uvicorn

from agentsystem.api import create_app

app = create_app()


def main() -> None:
    uvicorn.run(
        "agentsystem.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
