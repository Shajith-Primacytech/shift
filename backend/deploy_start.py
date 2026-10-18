"""One worker: model memory and in-process inference locks require one replica."""

import os


def command():
    port = int(os.environ.get("PORT", "10000"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid PORT")
    return [
        "/app/.venv/bin/python",
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
        "--workers",
        "1",
        "--no-access-log",
        "--proxy-headers",
        "--forwarded-allow-ips",
        "127.0.0.1",
    ]


if __name__ == "__main__":
    os.execv(command()[0], command())
