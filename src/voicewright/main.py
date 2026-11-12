"""Entry point: argument parsing, logging, single-instance IPC and Qt startup."""
from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from voicewright import APP_ID, APP_NAME, __version__
from voicewright.paths import logs_dir

COMMANDS = ("toggle", "start", "stop", "cancel", "show", "quit")


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    fh = RotatingFileHandler(logs_dir() / "voicewright.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    if sys.stderr is not None:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)


def _server_name() -> str:
    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    return f"{APP_ID}-{''.join(c for c in user if c.isalnum())}"


def _send_command(cmd: str) -> bool:
    """Send a command to a running instance. Returns True if one answered."""
    from PySide6.QtNetwork import QLocalSocket
    sock = QLocalSocket()
    sock.connectToServer(_server_name())
    if not sock.waitForConnected(400):
        return False
    sock.write(cmd.encode("utf-8"))
    sock.flush()
    sock.waitForBytesWritten(500)
    sock.disconnectFromServer()
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=APP_ID, description=f"{APP_NAME} – local voice dictation")
    group = parser.add_mutually_exclusive_group()
    for c in COMMANDS:
        group.add_argument(f"--{c}", action="store_const", const=c, dest="command",
                           help=f"send '{c}' to the running instance")
    parser.add_argument("--minimized", action="store_true", help="start in the tray")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    args = parser.parse_args(argv)

    # Single instance: forward CLI commands to an already running process
    # (done before creating the GUI so `voicewright --toggle` is instant).
    if _send_command(args.command or "show"):
        return 0
    if args.command in ("stop", "cancel", "quit"):
        print(f"{APP_NAME} is not running.", file=sys.stderr)
        return 1

    if sys.platform.startswith("linux") and os.environ.get("DISPLAY"):
        # XWayland bridges the clipboard even when dictation was started by
        # a desktop shortcut while another application had keyboard focus.
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

    from PySide6.QtCore import Qt
    from PySide6.QtNetwork import QLocalServer
    from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(False)

    _setup_logging(args.debug)
    log = logging.getLogger("voicewright")
    log.info("%s %s starting (%s)", APP_NAME, __version__, sys.platform)

    from voicewright.config import Config
    from voicewright.i18n import set_language

    config = Config()
    set_language(config.get("ui_language", "auto"))

    from voicewright.app import Controller
    from voicewright.i18n import tr

    if not QSystemTrayIcon.isSystemTrayAvailable():
        log.warning("No system tray available – the settings window will stay open.")

    controller = Controller(app, config)

    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    QLocalServer.removeServer(_server_name())
    if not server.listen(_server_name()):
        log.warning("IPC server failed: %s", server.errorString())

    def _on_connection() -> None:
        conn = server.nextPendingConnection()
        if conn is None:
            return

        def _read() -> None:
            data = bytes(conn.readAll()).decode("utf-8", "ignore").strip()
            if data in COMMANDS:
                controller.handle_command(data)

        conn.readyRead.connect(_read)
        conn.disconnected.connect(conn.deleteLater)
        if conn.bytesAvailable():
            _read()

    server.newConnection.connect(_on_connection)

    no_tray = not QSystemTrayIcon.isSystemTrayAvailable()
    controller.start(show_settings=(not args.minimized and args.command is None) or no_tray)
    if args.command in ("start", "toggle"):
        controller.handle_command(args.command)

    try:
        return app.exec()
    except Exception as exc:  # pragma: no cover
        log.exception("Fatal error")
        QMessageBox.critical(None, APP_NAME, tr("Fatal error:") + f"\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
