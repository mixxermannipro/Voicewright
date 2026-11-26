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
    from jeepney import MessageType

    with conn.filter(rule) as queue:
        msg = new_method_call(_addr(interface), method, signature, body)
        # Wait for the method reply first. Portal methods return a Request
        # handle right away; the result arrives later as a Response signal.
        # Reading only the signal would silently drop a D-Bus error reply
        # (for example an invalid restore token) and block until the timeout.
        started = time.monotonic()
        reply = conn.send_and_get_reply(msg, timeout=timeout)
        if getattr(reply.header, "message_type", None) == MessageType.error:
            name = reply.body[0] if reply.body else "org.freedesktop.DBus.Error.Failed"
            detail = reply.body[1] if len(reply.body) > 1 else ""
            raise PortalError(f"{name}: {detail}")
        remaining = max(0.1, timeout - (time.monotonic() - started))
        signal = conn.recv_until_filtered(queue, timeout=remaining)
    response = signal.body[0] if signal.body else 2
    if response == 1:
        raise PortalError("cancelled by user")
    if response != 0:
        raise PortalError("portal request failed")
    return _results(signal)


# ---------------------------------------------------------------------------
# Global shortcuts
# ---------------------------------------------------------------------------
class GlobalShortcutsPortal:
    """Press/release shortcut delivery through the compositor.

    ``on_press`` and ``on_release`` receive the shortcut id, so one portal
    session can serve the dictation and the rewrite shortcut.
    """

    def __init__(self, on_press: Optional[Callable[[str], None]] = None,
                 on_release: Optional[Callable[[str], None]] = None) -> None:
        self.on_press = on_press
        self.on_release = on_release
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._conn = None
        self._conn_lock = threading.Lock()
        self._state: dict[str, bool] = {"ok": False}
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

    def start(self, shortcuts=None, *, shortcut_id: str = "dictate",
              description: str = "Dictate", trigger: str = "CTRL+SHIFT+space",
              timeout: float = 60.0, wait: float = 0.4) -> bool:
        """Start listening for one or more shortcuts.

        ``shortcuts`` is a list of ``(id, description, trigger)`` tuples. The
        keyword arguments are the single-shortcut compatibility form.

        The compositor shows its permission dialog on its own schedule, so this
        returns after a short, bounded wait instead of blocking the caller for
        the full ``timeout``. A refusal that arrives later is reported through
        :attr:`error` and stops the loop.
        """
        if self._thread is not None and self._thread.is_alive():
            return bool(self._state.get("ok"))
        if shortcuts is None:
            shortcuts = [(shortcut_id, description, trigger)]
        elif isinstance(shortcuts, tuple) and len(shortcuts) == 3 and isinstance(shortcuts[0], str):
            shortcuts = [shortcuts]
        shortcuts = [tuple(s) for s in shortcuts if s and s[0]]
        if not shortcuts:
            self.error = "no shortcuts to bind"
            return False
        # Each run gets its own events. A previous thread may still be blocked
        # in a portal request after stop() timed out; if it shared these
        # events, a later start() would wake the old thread up again and two
        # listeners would deliver every shortcut twice.
        stop = threading.Event()
        ready = threading.Event()
        self._stop = stop
        # The result lives with the run, not on the object: an old thread that
        # times out must not overwrite the state of a newer run.
        state = {"ok": False}
        self._state = state
        self.error = ""
        self._thread = threading.Thread(
            target=self._run, args=(shortcuts, timeout, stop, ready, state),
            daemon=True, name="portal-shortcuts")
        self._thread.start()
        if ready.wait(max(0.0, wait)):
            return bool(state["ok"])
        # The compositor is still showing its permission dialog. Report the
        # optimistic state and let the loop finish in the background.
        return self._thread.is_alive()

    def _run(self, shortcuts: list[tuple], timeout: float,
             stop: threading.Event, ready: threading.Event,
             state: dict[str, bool]) -> None:
        try:
            self._loop(shortcuts, timeout, stop, ready, state)
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            log.warning("GlobalShortcuts portal failed: %s", exc)
        finally:
            ready.set()

    def _loop(self, shortcuts: list[tuple], timeout: float,
              stop: threading.Event, ready: threading.Event,
              state: dict[str, bool]) -> None:
        _, MatchRule, _, _, open_conn = _imports()
        conn = open_conn(bus="SESSION")
        with self._conn_lock:
            self._conn = conn
        try:
            if stop.is_set():
                return
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

            bind_list = []
            for sid, desc, trigger in shortcuts:
                options = {"description": ("s", desc or sid)}
                if trigger:
                    options["preferred_trigger"] = ("s", trigger)
                bind_list.append((sid, options))

            bind_results = _request(
                conn, IFACE_SHORTCUTS, "BindShortcuts", "oa(sa{sv})sa{sv}",
                (session, bind_list, "", {"handle_token": ("s", _token("vw_bind"))}),
                _token("vw_req_bind"), timeout=timeout,
            )
            bound = bind_results.get("shortcuts") or []
            bound_ids = {item[0] for item in bound if item and item[0]}
            if not bound_ids:
                raise PortalError("compositor did not bind the shortcut")

            # ListShortcuts is optional in older portal versions. It tells us
            # which of the requested shortcuts really exist after the user
            # edited them in the compositor dialog.
            try:
                listed = _request(
                    conn, IFACE_SHORTCUTS, "ListShortcuts", "oa{sv}",
                    (session, {"handle_token": ("s", _token("vw_list"))}),
                    _token("vw_req_list"), timeout=min(timeout, 8.0),
                )
                listed_ids = {item[0] for item in (listed.get("shortcuts") or [])
                              if item and item[0]}
                if listed_ids:
                    bound_ids &= listed_ids
                    log.info("Global shortcuts bound: %s", ", ".join(sorted(bound_ids)))
            except PortalError as exc:
                log.debug("ListShortcuts unavailable: %s", exc)

            if not bound_ids:
                raise PortalError("no usable shortcut was bound")

            state["ok"] = True
            ready.set()

            rule = MatchRule(type="signal", interface=IFACE_SHORTCUTS)
            with conn.filter(rule) as queue:
                while not stop.is_set():
                    try:
                        msg = conn.recv_until_filtered(queue, timeout=0.5)
                    except TimeoutError:
                        continue
                    self._dispatch(msg, session, bound_ids)
        finally:
            with self._conn_lock:
                if self._conn is conn:
                    self._conn = None
            conn.close()

    def _dispatch(self, msg, session: str, shortcut_ids) -> None:
        from jeepney import HeaderFields

        try:
            # Header field 3 is MEMBER; field 9 is UNIX_FDS. The old lookup
            # returned None, so no portal shortcut ever reached the detector.
            member = msg.header.fields.get(HeaderFields.member)
        except Exception:
            member = None
        body = msg.body or ()
        shortcut_id = None
        if len(body) >= 2:
            incoming_session, shortcut_id = body[0], body[1]
            if incoming_session != session:
                return
            if isinstance(shortcut_ids, str):
                if shortcut_id != shortcut_ids:
                    return
            elif shortcut_id not in shortcut_ids:
                return
        elif isinstance(shortcut_ids, str):
            shortcut_id = shortcut_ids
        else:
            return
        if member == "Activated":
            try:
                if self.on_press is not None:
                    self.on_press(shortcut_id)
            except Exception:  # noqa: BLE001
                log.exception("Shortcut press handler failed")
        elif member == "Deactivated":
            try:
                if self.on_release is not None:
                    self.on_release(shortcut_id)
            except Exception:  # noqa: BLE001
                log.exception("Shortcut release handler failed")

    def stop(self) -> None:
        self._stop.set()
        # Closing the connection unblocks a thread that is still waiting for
        # a portal reply, so it cannot start listening again after a restart.
        with self._conn_lock:
            conn, self._conn = self._conn, None
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None


# ---------------------------------------------------------------------------
# Remote desktop (keyboard injection)
# ---------------------------------------------------------------------------
class RemoteDesktopPortal:
    """Keyboard control granted by the compositor after an explicit dialog.

    ``persist_mode=2`` asks the portal to keep the permission until the user
    revokes it. The returned ``restore_token`` is stored by the caller and
    reused on the next start, so the dialog appears only once. The portal
    invalidates a token after one use and returns a fresh one; the callback
    updates the stored value every time.
    """

    def __init__(self, on_restore_token: Optional[Callable[[str], None]] = None) -> None:
        self._conn = None
        self._session: Optional[str] = None
        self.error = ""
        self.restore_token = ""
        self.on_restore_token = on_restore_token
        self._lock = threading.Lock()
        self._connecting = False

    @property
    def connected(self) -> bool:
        return self._conn is not None and self._session is not None

    def connect(self, timeout: float = 90.0, restore_token: str = "") -> bool:
        # Do not hold the lock while the compositor shows its dialog: key
        # injection must be able to report "not ready" immediately instead of
        # freezing the Qt main thread behind a blocking connect().
        with self._lock:
            if self.connected:
                return True
            if self._connecting:
                return False
            self._connecting = True
        try:
            self._connect(timeout, restore_token)
            return True
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            log.warning("RemoteDesktop portal failed: %s", exc)
            with self._lock:
                self._close()
            return False
        finally:
            with self._lock:
                self._connecting = False

    def _connect(self, timeout: float, restore_token: str = "") -> None:
        _, _, _, _, open_conn = _imports()
        conn = open_conn(bus="SESSION")
        with self._lock:
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

        options = {
            "types": ("u", 1),          # 1 = keyboard
            "persist_mode": ("u", 2),   # 2 = persist until explicitly revoked
            "handle_token": ("s", _token("vw_dev")),
        }
        if restore_token:
            options["restore_token"] = ("s", restore_token)
        try:
            _request(
                conn, IFACE_REMOTE, "SelectDevices", "oa{sv}",
                (session, options),
                _token("vw_rd_dev"), timeout=timeout,
            )
        except PortalError as exc:
            if restore_token or "InvalidArgument" not in str(exc):
                # A rejected restore token means the permission was revoked.
                # Fail quietly: the caller clears the token and falls back to
                # wtype or the clipboard instead of opening a dialog at start.
                raise
            # Portal version 1 has neither persist_mode nor restore_token.
            # Retry with the plain keyboard request instead of failing.
            log.info("RemoteDesktop persistence unavailable (%s); retrying without it", exc)
            _request(
                conn, IFACE_REMOTE, "SelectDevices", "oa{sv}",
                (session, {"types": ("u", 1),
                           "handle_token": ("s", _token("vw_dev"))}),
                _token("vw_rd_dev2"), timeout=timeout,
            )

        start_results = _request(
            conn, IFACE_REMOTE, "Start", "osa{sv}",
            (session, "", {"handle_token": ("s", _token("vw_start"))}),
            _token("vw_rd_start"), timeout=timeout,
        )
        # Only now is the keyboard really usable. Until Start() succeeded the
        # permission dialog may still be open, so connected must stay False.
        with self._lock:
            if self._conn is not conn:
                raise PortalError("connection closed during setup")
            self._session = session

        fresh = start_results.get("restore_token")
        if isinstance(fresh, tuple):
            fresh = fresh[1]
        if fresh:
            self.restore_token = str(fresh)
            if self.on_restore_token is not None:
                try:
                    self.on_restore_token(self.restore_token)
                except Exception:  # noqa: BLE001
                    log.exception("Could not store the portal restore token")

    def key(self, keycode: int, pressed: bool) -> bool:
        if not self.connected:
            return False
        try:
            _, _, _, new_method_call, _ = _imports()
            msg = new_method_call(
                _addr(IFACE_REMOTE), "NotifyKeyboardKeycode", "oa{sv}iu",
                (self._session, {}, keycode, 1 if pressed else 0),
            )
            # Never block the UI thread behind another portal call. A short
            # timeout degrades to wtype/clipboard instead of freezing.
            if not self._lock.acquire(timeout=0.25):
                log.debug("Portal is busy; skipping key injection")
                return False
            try:
                if self._conn is None:
                    return False
                reply = self._conn.send_and_get_reply(msg, timeout=2.0)
            finally:
                self._lock.release()
            from jeepney import MessageType
            if getattr(reply.header, "message_type", None) == MessageType.error:
                # The permission was revoked or the session expired. Report
                # failure so the caller can fall back to wtype/clipboard.
                log.info("Portal key injection rejected: %s", reply.body)
                return False
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
