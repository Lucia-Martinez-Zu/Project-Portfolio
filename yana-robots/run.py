"""Yana Robots server entry point."""

import logging

from app import create_app
from app.config import Config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app, socketio, _ = create_app()
    print(
        f"\n  Yana Robots running on http://{Config.HOST}:{Config.PORT}\n"
        f"  Source: {Config.TELEMETRY_SOURCE} | Update rate: {Config.UPDATE_HZ} Hz\n"
    )
    socketio.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
        allow_unsafe_werkzeug=True,
    )


if __name__ == "__main__":
    main()
