"""Wayland desktop portals over D-Bus (jeepney).

Two portals are used:

``org.freedesktop.portal.GlobalShortcuts``
    Delivers shortcut press and release events, so tap-to-toggle and
    hold-to-talk both work on Wayland. The compositor asks the user once.

``org.freedesktop.portal.RemoteDesktop``
    Injects Ctrl+V through the compositor after the user grants keyboard
    control. No root, no ``/dev/uinput``, no raw device access.

Everything degrades gracefully: a missing portal, a refused permission or a
different compositor implementation returns ``False`` and the caller falls
back to ``wtype``, ``ydotool`` (opt-in) or the clipboard.
"""
from __future__ import annotations

import logging
import secrets
import threading
import time
from typing import Callable, Optional

log = logging.getLogger(__name__)

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
IFACE_SHORTCUTS = "org.freedesktop.portal.GlobalShortcuts"
IFACE_REMOTE = "org.freedesktop.portal.RemoteDesktop"
IFACE_REQUEST = "org.freedesktop.portal.Request"

KEY_LEFTCTRL = 29
KEY_LEFTSHIFT = 42
KEY_V = 47
KEY_C = 46
KEY_X = 45
KEY_A = 30


class PortalError(Exception):
    pass


def _imports():
    try:
        from jeepney import DBusAddress, MatchRule, message_bus, new_method_call  # type: ignore
        from jeepney.io.blocking import open_dbus_connection  # type: ignore
        return (DBusAddress, MatchRule, message_bus, new_method_call, open_dbus_connection)
    except Exception as exc:  # noqa: BLE001
        raise PortalError("jeepney is not installed") from exc


def _addr(interface: str):
    DBusAddress = _imports()[0]
    return DBusAddress(PORTAL_PATH, bus_name=PORTAL_BUS, interface=interface)


def _token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def predict_request_path(unique_name: str, token: str) -> str:
    """The request handle the portal will use for a given token."""
    sender = unique_name.lstrip(":").replace(".", "_")
    return f"/org/freedesktop/portal/desktop/request/{sender}/{token}"


def _unwrap(value):
    """jeepney decodes a variant as (signature, value); flatten it."""
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], str):
        return _unwrap(value[1])
    if isinstance(value, dict):
        return {k: _unwrap(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_unwrap(v) for v in value]
    return value


def _results(msg) -> dict:
    """Extract the results dict from a Request.Response signal."""
    body = msg.body
    if not body or len(body) < 2:
        return {}
    response, results = body[0], body[1]
    if response not in (0, 1):
        # 1 = cancelled by the user, 2 = other error
        log.info("Portal request finished with response %s", response)
    return _unwrap(results)


def _request(conn, interface: str, method: str, signature: str, body: tuple,
             token: str, timeout: float = 60.0) -> dict:
    """Call a portal method that answers through a Request.Response signal."""
    MatchRule, new_method_call = _imports()[1], _imports()[3]
    path = predict_request_path(conn.unique_name, token)
    rule = MatchRule(type="signal", interface=IFACE_REQUEST, member="Response", path=path)
    with conn.filter(rule) as queue:
        msg = new_method_call(_addr(interface), method, signature, body)
        conn.send(msg)
        reply = conn.recv_until_filtered(queue, timeout=timeout)
    return _results(reply)


# ---------------------------------------------------------------------------
# Global shortcuts
# ---------------------------------------------------------------------------
class GlobalShortcutsPortal:
    """Press/release shortcut delivery through the compositor."""

    def __init__(self, on_press: Callable[[], None],
                 on_release: Callable[[], None]) -> None:
        self.on_press = on_press
        self.on_release = on_release
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._ok = False
        self.error = ""

    def available(self) -> bool:
        try:
            _imports()
        except PortalError:
            return False
        try:
            conn = _imports()[4](bus="SESSION")
        except Exception:  # noqa: BLE001
            return False
        conn.close()
        return True

    def start(self, shortcut_id: str = "dictate", description: str = "Dictate",
              trigger: str = "CTRL+SHIFT+SPACE", timeout: float = 60.0,
              wait: float = 0.4) -> bool:
        """Start listening.

        The compositor shows its permission dialog on its own schedule, so this
        returns after a short, bounded wait instead of blocking the caller for
        the full ``timeout``. A refusal that arrives later is reported through
        :attr:`error` and stops the loop.
        """
        if self._thread is not None and self._thread.is_alive():
            return self._ok
        self._stop.clear()
        self._ready.clear()
        self._ok = False
        self.error = ""
        self._thread = threading.Thread(
            target=self._run, args=(shortcut_id, description, trigger, timeout),
            daemon=True, name="portal-shortcuts")
        self._thread.start()
        self._ready.wait(max(0.0, wait))
        return self._ok or self._thread.is_alive()

    def _run(self, shortcut_id: str, description: str, trigger: str, timeout: float) -> None:
        try:
            self._loop(shortcut_id, description, trigger, timeout)
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            log.warning("GlobalShortcuts portal failed: %s", exc)
        finally:
            self._ok = False
            self._ready.set()

    def _loop(self, shortcut_id: str, description: str, trigger: str, timeout: float) -> None:
        DBusAddress, MatchRule, _, new_method_call, open_conn = _imports()
        conn = open_conn(bus="SESSION")
        try:
            session_token = _token("vw_session")
            results = _request(
                conn, IFACE_SHORTCUTS, "CreateSession", "a{sv}",
                ({"handle_token": ("s", _token("vw_req")),
                  "session_handle_token": ("s", session_token)},),
                _token("vw_req_create"), timeout=timeout,
            )
            session = results.get("session_handle")
            if not session:
                raise PortalError("no session handle")
            if isinstance(session, tuple):
                session = session[1]

            bind_results = _request(
                conn, IFACE_SHORTCUTS, "BindShortcuts", "oa(sa{sv})sa{sv}",
                (
                    session,
                    [(shortcut_id, {"description": ("s", description),
                                    "preferred_trigger": ("s", trigger)})],
                    "",
                    {"handle_token": ("s", _token("vw_bind"))},
                ),
                _token("vw_req_bind"), timeout=timeout,
            )
            bound = bind_results.get("shortcuts") or []
            if not bound:
                raise PortalError("compositor did not bind the shortcut")

            self._ok = True
            self._ready.set()

            rule = MatchRule(type="signal", interface=IFACE_SHORTCUTS)
            with conn.filter(rule) as queue:
                while not self._stop.is_set():
                    try:
                        msg = conn.recv_until_filtered(queue, timeout=0.5)
                    except TimeoutError:
                        continue
                    self._dispatch(msg, session, shortcut_id)
        finally:
            conn.close()

    def _dispatch(self, msg, session: str, shortcut_id: str) -> None:
        try:
            member = msg.header.fields.get(9) or msg.header.fields.get("member")
        except Exception:
            member = None
        body = msg.body or ()
        if len(body) >= 2:
            incoming_session, incoming_id = body[0], body[1]
            if incoming_session != session or incoming_id != shortcut_id:
                return
        if member == "Activated":
            try:
                self.on_press()
            except Exception:  # noqa: BLE001
                log.exception("Shortcut press handler failed")
        elif member == "Deactivated":
            try:
                self.on_release()
            except Exception:  # noqa: BLE001
                log.exception("Shortcut release handler failed")

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None


# ---------------------------------------------------------------------------
# Remote desktop (keyboard injection)
# ---------------------------------------------------------------------------
class RemoteDesktopPortal:
    """Keyboard control granted by the compositor after an explicit dialog."""

    def __init__(self) -> None:
        self._conn = None
        self._session: Optional[str] = None
        self.error = ""
        self._lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._conn is not None and self._session is not None

    def connect(self, timeout: float = 90.0) -> bool:
        with self._lock:
            if self.connected:
                return True
            try:
                self._connect(timeout)
                return True
            except Exception as exc:  # noqa: BLE001
                self.error = str(exc)
                log.warning("RemoteDesktop portal failed: %s", exc)
                self._close()
                return False

    def _connect(self, timeout: float) -> None:
        _, _, _, _, open_conn = _imports()
        conn = open_conn(bus="SESSION")
        self._conn = conn
        token = _token("vw_rd")
        results = _request(
            conn, IFACE_REMOTE, "CreateSession", "a{sv}",
            ({"handle_token": ("s", _token("vw_req")),
              "session_handle_token": ("s", token)},),
            _token("vw_rd_create"), timeout=timeout,
        )
        session = results.get("session_handle")
        if not session:
            raise PortalError("no remote desktop session")
        self._session = session

        _request(
            conn, IFACE_REMOTE, "SelectDevices", "oa{sv}",
            (session, {"types": ("u", 1),  # 1 = keyboard
                       "handle_token": ("s", _token("vw_dev"))}),
            _token("vw_rd_dev"), timeout=timeout,
        )
        _request(
            conn, IFACE_REMOTE, "Start", "osa{sv}",
            (session, "", {"handle_token": ("s", _token("vw_start"))}),
            _token("vw_rd_start"), timeout=timeout,
        )

    def key(self, keycode: int, pressed: bool) -> bool:
        if not self.connected:
            return False
        try:
            _, _, _, new_method_call, _ = _imports()
            msg = new_method_call(
                _addr(IFACE_REMOTE), "NotifyKeyboardKeycode", "oa{sv}iu",
                (self._session, {}, keycode, 1 if pressed else 0),
            )
            self._conn.send(msg)
            return True
        except Exception as exc:  # noqa: BLE001
            log.debug("Portal key injection failed: %s", exc)
            return False

    def paste(self, ctrl_shift: bool = False, key: str = "v") -> bool:
        """Send Ctrl(+Shift)+V (or C) through the portal."""
        if not self.connected:
            return False
        code = {"v": KEY_V, "c": KEY_C, "x": KEY_X, "a": KEY_A}.get(key.lower(), KEY_V)
        ok = self.key(KEY_LEFTCTRL, True)
        if ctrl_shift:
            ok = self.key(KEY_LEFTSHIFT, True) and ok
        time.sleep(0.01)
        ok = self.key(code, True) and ok
        ok = self.key(code, False) and ok
        if ctrl_shift:
            ok = self.key(KEY_LEFTSHIFT, False) and ok
        ok = self.key(KEY_LEFTCTRL, False) and ok
        return ok

    def disconnect(self) -> None:
        with self._lock:
            self._close()

    def _close(self) -> None:
        conn, self._conn = self._conn, None
        self._session = None
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
