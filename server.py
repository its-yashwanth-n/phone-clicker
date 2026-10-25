"""Phone Clicker - use your phone as a presentation remote.

Run this on your laptop, scan the QR code with your phone, and the phone
becomes a clicker for PowerPoint, Google Slides, PDFs, media and more.
Key presses are sent to whichever window is focused on the laptop.
"""

import argparse
import asyncio
import hashlib
import hmac
import io
import json
import math
import os
import re
import secrets
import socket
import sys
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import qrcode
import qrcode.image.svg
from aiohttp import WSMsgType, web
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key
from pynput.mouse import Button
from pynput.mouse import Controller as MouseController

try:  # Windows only: lets us read the current slide straight from PowerPoint.
    import pythoncom
    import win32com.client
except ImportError:
    win32com = None

__version__ = "1.1.0"

# When packaged with PyInstaller, bundled files are unpacked to sys._MEIPASS.
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
STATIC_DIR = BASE_DIR / "static"
IS_MAC = sys.platform == "darwin"
CMD = Key.cmd if IS_MAC else Key.ctrl

keyboard = KeyboardController()
mouse = MouseController()

# Each shortcut is a list of keys pressed together, modifiers first.
SHORTCUTS = {
    "next": [Key.right],
    "prev": [Key.left],
    "first": [Key.home],
    "last": [Key.end],
    "end_show": [Key.esc],
    "black": ["b"],
    "white": ["w"],
    "fullscreen": [Key.f11],
    "zoom_in": [CMD, "="],
    "zoom_out": [CMD, "-"],
    "zoom_reset": [CMD, "0"],
    "page_down": [Key.page_down],
    "page_up": [Key.page_up],
    "play_pause": [Key.media_play_pause],
    "media_next": [Key.media_next],
    "media_prev": [Key.media_previous],
    "volume_up": [Key.media_volume_up],
    "volume_down": [Key.media_volume_down],
    "mute": [Key.media_volume_mute],
    "space": [Key.space],
    "enter": [Key.enter],
    "backspace": [Key.backspace],
    "tab": [Key.tab],
    "up": [Key.up],
    "down": [Key.down],
    "switch_app": [Key.cmd, Key.tab] if IS_MAC else [Key.alt, Key.tab],
}

# "Start slideshow" differs per app, so each profile defines its own.
if IS_MAC:
    PROFILES = {
        "powerpoint": {"start": [Key.cmd, Key.shift, Key.enter], "start_here": [Key.cmd, Key.enter]},
        "powerpoint_web": {"start": [Key.cmd, Key.shift, Key.enter], "start_here": [Key.cmd, Key.enter]},
        "google_slides": {"start": [Key.cmd, Key.shift, Key.enter], "start_here": [Key.cmd, Key.enter]},
        "keynote": {"start": [Key.alt, Key.cmd, "p"]},
        "pdf": {"start": [Key.cmd, "l"], "start_here": [Key.cmd, Key.ctrl, "f"]},
    }
else:
    PROFILES = {
        "powerpoint": {"start": [Key.f5], "start_here": [Key.shift, Key.f5]},
        "powerpoint_web": {"start": [Key.ctrl, Key.f5]},
        "google_slides": {"start": [Key.ctrl, Key.shift, Key.f5], "start_here": [Key.ctrl, Key.f5]},
        "pdf": {"start": [Key.ctrl, "l"], "start_here": [Key.f11]},
    }

# PDF viewers page more reliably with Page Up/Down than with arrow keys.
PROFILES["pdf"].update({"next": [Key.page_down], "prev": [Key.page_up]})


def press_combo(keys):
    *modifiers, last = keys
    for mod in modifiers:
        keyboard.press(mod)
    try:
        keyboard.tap(last)
    finally:
        for mod in reversed(modifiers):
            keyboard.release(mod)


def handle_message(msg):
    kind = msg.get("type")
    if kind == "key":
        action = msg.get("action")
        profile = PROFILES.get(msg.get("profile"), {})
        keys = profile.get(action) or SHORTCUTS.get(action)
        if keys:
            press_combo(keys)
    elif kind == "move":
        mouse.move(int(msg.get("dx", 0)), int(msg.get("dy", 0)))
    elif kind == "click":
        button = Button.right if msg.get("button") == "right" else Button.left
        mouse.click(button, 2 if msg.get("double") else 1)
    elif kind == "scroll":
        mouse.scroll(0, int(msg.get("dy", 0)))
    elif kind == "text":
        keyboard.type(str(msg.get("text", ""))[:500])


def config_dir():
    if os.environ.get("PHONE_CLICKER_CONFIG_DIR"):  # used by tests
        return Path(os.environ["PHONE_CLICKER_CONFIG_DIR"])
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "PhoneClicker"
    if IS_MAC:
        return Path.home() / "Library" / "Application Support" / "PhoneClicker"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "phone-clicker"


# SRP-6a (RFC 5054) lets a phone prove it knows the passcode without sending it, and without
# sending anything a Wi-Fi eavesdropper could use to guess it offline. Every guess has to go
# through the laptop, where Guard limits them. Group: the RFC 5054 2048-bit safe prime, g = 2.
SRP_N = int(
    "AC6BDB41324A9A9BF166DE5E1389582FAF72B6651987EE07FC3192943DB56050A37329CBB4A099ED8193E0757767A13DD52312AB4B03310D"
    "CD7F48A9DA04FD50E8083969EDB767B0CF6095179A163AB3661A05FBD5FAAAE82918A9962F0B93B855F97993EC975EEAA80D740ADBF4FF74"
    "7359D041D5C33EA71D281E446B14773BCA97B43A23FB801676BD207A436C6481F1D2B9078717461A5B9D32E688F87748544523B524B0D57D"
    "5EA77A2775D2ECFA032CFBDBF52FB3786160279004E57AE6AF874E7303CE53299CCC041C7BC308D82A5698F3A8D0C38271AE35F8E9DBFBB6"
    "94B5C803D89F7AE435DE236D525F54759B65E372FCD68EF20FA7111F9E4AFF73",
    16,
)
SRP_G = 2


def srp_pad(n):
    return n.to_bytes(256, "big")


def sha256(*parts):
    return hashlib.sha256(b"".join(parts)).digest()


SRP_K = int.from_bytes(sha256(srp_pad(SRP_N), srp_pad(SRP_G)), "big")


class Passcode:
    """The 4-8 digit passcode phones must enter.

    Only an SRP verifier is saved (g^x mod N, with x = PBKDF2 of the passcode), never the digits.
    """

    PATTERN = re.compile(r"^\d{4,8}$")
    ITERATIONS = 100_000  # the phone computes this in plain JavaScript, so keep it phone-friendly

    def __init__(self):
        self.file = config_dir() / "config.json"
        try:
            record = json.loads(self.file.read_text(encoding="utf-8")).get("passcode")
        except (OSError, ValueError):
            record = None
        # Ignore records from older test builds that stored a different format.
        self.record = record if isinstance(record, dict) and "verifier" in record else None

    @property
    def is_set(self):
        return bool(self.record)

    @staticmethod
    def derive_x(code, salt, iterations):
        return int.from_bytes(hashlib.pbkdf2_hmac("sha256", code.encode(), salt, iterations), "big")

    def set(self, code):
        salt = secrets.token_bytes(16)
        x = self.derive_x(code, salt, self.ITERATIONS)
        self.record = {
            "salt": salt.hex(),
            "iterations": self.ITERATIONS,
            "verifier": format(pow(SRP_G, x, SRP_N), "x"),
        }
        self.file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"passcode": self.record}, indent=2), encoding="utf-8")
        tmp.replace(self.file)

    def check(self, code):
        """Direct check, used by the laptop page when changing the passcode."""
        if not self.record or not isinstance(code, str) or not self.PATTERN.match(code):
            return False
        r = self.record
        x = self.derive_x(code, bytes.fromhex(r["salt"]), r["iterations"])
        return secrets.compare_digest(format(pow(SRP_G, x, SRP_N), "x"), r["verifier"])

    def challenge(self):
        """Starts one login attempt. Returns (secret state, public challenge for the phone)."""
        v = int(self.record["verifier"], 16)
        b = secrets.randbits(256)
        B = (SRP_K * v + pow(SRP_G, b, SRP_N)) % SRP_N
        public = {"salt": self.record["salt"], "iterations": self.record["iterations"], "B": format(B, "x")}
        return (b, B, v), public

    @staticmethod
    def verify(state, A_hex, M1_hex):
        """Checks the phone's proof. Returns the shared session key, or None if it's wrong."""
        b, B, v = state
        try:
            A = int(A_hex, 16)
            M1 = bytes.fromhex(M1_hex)
        except (TypeError, ValueError):
            return None
        if A % SRP_N == 0:
            return None
        u = int.from_bytes(sha256(srp_pad(A), srp_pad(B)), "big")
        if u == 0:
            return None
        S = pow(A * pow(v, u, SRP_N) % SRP_N, b, SRP_N)
        if not secrets.compare_digest(sha256(srp_pad(A), srp_pad(B), srp_pad(S)), M1):
            return None
        return sha256(srp_pad(S))


def device_key(session_key):
    # Both sides derive this from the SRP session key, so it never crosses the network.
    return hmac.new(session_key, b"phone-clicker-device", hashlib.sha256).digest()


class Guard:
    """Slows down passcode guessing.

    Each phone (IP address) gets 5 tries, then a lockout that doubles every time
    (30 s, 1 min, 2 min ... up to 15 min). 20 wrong tries from anywhere within
    5 minutes locks everyone out for 5 minutes.
    """

    TRIES = 5

    def __init__(self):
        self.fails = {}
        self.lockouts = {}
        self.locked_until = {}
        self.recent = []
        self.global_until = 0.0

    def wait(self, ip):
        until = max(self.locked_until.get(ip, 0.0), self.global_until)
        return max(0, math.ceil(until - time.monotonic()))

    def fail(self, ip):
        now = time.monotonic()
        self.recent = [t for t in self.recent if now - t < 300] + [now]
        if len(self.recent) >= 20:
            self.global_until = now + 300
            self.recent.clear()
        self.fails[ip] = self.fails.get(ip, 0) + 1
        if self.fails[ip] >= self.TRIES:
            self.fails[ip] = 0
            self.lockouts[ip] = self.lockouts.get(ip, 0) + 1
            self.locked_until[ip] = now + min(30 * 2 ** (self.lockouts[ip] - 1), 900)
        return self.TRIES - self.fails[ip]

    def success(self, ip):
        self.fails.pop(ip, None)
        self.lockouts.pop(ip, None)


def count_displays():
    """How many screens are attached (including mirrored ones), or None if unknown.

    Used to warn before showing the QR code or passcode form while a projector is plugged in.
    """
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class DisplayDevice(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("DeviceName", wintypes.WCHAR * 32),
                    ("DeviceString", wintypes.WCHAR * 128),
                    ("StateFlags", wintypes.DWORD),
                    ("DeviceID", wintypes.WCHAR * 128),
                    ("DeviceKey", wintypes.WCHAR * 128),
                ]

            def devices(parent):
                i = 0
                while True:
                    dev = DisplayDevice(cb=ctypes.sizeof(DisplayDevice))
                    if not ctypes.windll.user32.EnumDisplayDevicesW(parent, i, ctypes.byref(dev), 0):
                        return
                    yield dev
                    i += 1

            active = 0x1  # DISPLAY_DEVICE_ATTACHED_TO_DESKTOP for adapters, DISPLAY_DEVICE_ACTIVE for monitors
            return sum(
                1
                for adapter in devices(None) if adapter.StateFlags & active
                for monitor in devices(adapter.DeviceName) if monitor.StateFlags & active
            ) or None
        if IS_MAC:
            import Quartz
            _err, _ids, count = Quartz.CGGetOnlineDisplayList(16, None, None)
            return count or None
    except Exception:
        pass
    return None


class PowerPointWatcher:
    """Reads the current slide number from PowerPoint (Windows desktop app) over COM."""

    def __init__(self):
        # COM objects must stay on the thread that created them, so use one worker thread.
        self.executor = ThreadPoolExecutor(max_workers=1, initializer=pythoncom.CoInitialize)

    def read(self):
        try:
            app = win32com.client.GetActiveObject("PowerPoint.Application")
        except Exception:
            return None
        try:
            if app.SlideShowWindows.Count:
                window = app.SlideShowWindows(1)
                return {
                    "mode": "show",
                    "current": window.View.Slide.SlideIndex,
                    "total": window.Presentation.Slides.Count,
                }
            return {
                "mode": "edit",
                "current": app.ActiveWindow.View.Slide.SlideIndex,
                "total": app.ActivePresentation.Slides.Count,
            }
        except Exception:  # no presentation open, or the "end of slide show" screen
            return None

    async def watch(self, app):
        loop = asyncio.get_running_loop()
        last = None
        while True:
            if app["sockets"]:
                info = await loop.run_in_executor(self.executor, self.read)
                if info != last:
                    last = app["slide"] = info
                    await broadcast(app, {"type": "slide", "info": info})
            await asyncio.sleep(0.5)


async def broadcast(app, msg):
    for ws in list(app["sockets"]):
        try:
            await ws.send_json(msg)
        except ConnectionError:
            pass


def get_lan_ip():
    # Connecting a UDP socket sends nothing; it just picks the outgoing interface.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


LOCAL_HOSTS = ("localhost", "127.0.0.1", "[::1]")


def is_local(request):
    """True only for the laptop's own browser.

    Also checks the Host and Origin headers, so a website open on the laptop
    can't reach these pages through the browser (DNS rebinding or cross-site POSTs).
    """
    if request.remote not in ("127.0.0.1", "::1"):
        return False
    if request.host.rsplit(":", 1)[0] not in LOCAL_HOSTS:
        return False
    origin = request.headers.get("Origin")
    return origin is None or origin == f"http://{request.host}"


def require_local(handler):
    async def wrapper(request):
        if not is_local(request):
            raise web.HTTPForbidden()
        return await handler(request)
    return wrapper


async def index(request):
    return web.FileResponse(STATIC_DIR / "index.html")


@require_local
async def connect_page(request):
    return web.FileResponse(STATIC_DIR / "connect.html")


@require_local
async def api_status(request):
    app = request.app
    displays = await asyncio.get_running_loop().run_in_executor(None, count_displays)
    return web.json_response({
        "version": __version__,
        "passcodeSet": app["passcode"].is_set,
        "phones": len(app["sockets"]),
        "displays": displays,
    })


@require_local
async def api_qr(request):
    # Only handed out once a passcode exists, so a phone can never connect without one.
    if not request.app["passcode"].is_set:
        raise web.HTTPConflict(text="Set a passcode first")
    url = request.app["phone_url"]
    buf = io.BytesIO()
    qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12).save(buf)
    return web.json_response({"url": url, "svg": buf.getvalue().decode()})


@require_local
async def api_passcode(request):
    app = request.app
    passcode = app["passcode"]
    try:
        body = await request.json()
    except ValueError:
        raise web.HTTPBadRequest()
    new = body.get("passcode")
    if not isinstance(new, str) or not Passcode.PATTERN.match(new):
        return web.json_response({"error": "The passcode must be 4 to 8 digits."}, status=400)
    if passcode.is_set:
        loop = asyncio.get_running_loop()
        if not await loop.run_in_executor(None, passcode.check, body.get("current")):
            return web.json_response({"error": "Your current passcode is wrong."}, status=403)
    passcode.set(new)
    # Every phone has to enter the new passcode.
    app["devices"].clear()
    for ws in list(app["sockets"]):
        await ws.close(code=4001, message=b"passcode changed")
    print("Passcode saved.")
    return web.json_response({"ok": True})


@require_local
async def quit_app(request):
    # The "Stop" button on the laptop's QR page. Needed for the packaged Mac app,
    # which has no terminal window to close.
    print("Stopped from the QR page.")
    asyncio.get_running_loop().call_later(0.3, os._exit, 0)
    return web.Response(text="stopped")


async def authenticate(ws, request):
    """Waits for the phone to prove it knows the passcode (or holds a key from an earlier unlock).

    Every message that asks the phone to (re)try carries a fresh challenge:
      - SRP values (salt, iterations, B) for a passcode attempt
      - a random nonce the phone signs with its saved device key to skip the passcode
    Neither the passcode nor the device key is ever sent.
    """
    app = request.app
    ip = request.remote
    guard = app["guard"]
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 300
    attempt = {}

    def challenge():
        attempt["srp"], public = app["passcode"].challenge()
        attempt["nonce"] = secrets.token_hex(16)
        return {**public, "nonce": attempt["nonce"]}

    await ws.send_json({"type": "challenge", **challenge()})

    while (left := deadline - loop.time()) > 0:
        try:
            msg = await asyncio.wait_for(ws.receive(), left)
        except asyncio.TimeoutError:
            break
        if msg.type != WSMsgType.TEXT:
            if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED, WSMsgType.ERROR):
                return False
            continue
        try:
            data = json.loads(msg.data)
        except ValueError:
            continue
        if not isinstance(data, dict) or data.get("type") != "auth":
            continue

        # Same browser reconnecting (refresh, screen lock, Wi-Fi blip): it signs the nonce
        # with the key it derived at its last unlock, so there's no need to retype.
        device_id = data.get("device")
        if isinstance(device_id, str) and device_id in app["devices"]:
            expected = hmac.new(app["devices"][device_id], attempt["nonce"].encode(), hashlib.sha256).hexdigest()
            if secrets.compare_digest(str(data.get("proof", "")), expected):
                await ws.send_json({"type": "auth_ok", "device": device_id})
                return True

        if "A" not in data:
            await ws.send_json({"type": "auth_required", **challenge()})
            continue
        if wait := guard.wait(ip):
            await ws.send_json({"type": "locked", "seconds": wait, **challenge()})
            continue
        session_key = Passcode.verify(attempt["srp"], data.get("A"), data.get("M1"))
        if session_key:
            guard.success(ip)
            device_id = secrets.token_urlsafe(16)
            app["devices"][device_id] = device_key(session_key)
            await ws.send_json({"type": "auth_ok", "device": device_id})
            return True

        remaining = guard.fail(ip)
        print(f"Wrong passcode from {ip}")
        if wait := guard.wait(ip):
            await ws.send_json({"type": "locked", "seconds": wait, **challenge()})
        else:
            await ws.send_json({"type": "auth_fail", "remaining": remaining, **challenge()})
    return False


async def websocket(request):
    if not secrets.compare_digest(request.query.get("t", ""), request.app["token"]):
        raise web.HTTPForbidden()

    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)

    if not request.app["passcode"].is_set:
        await ws.send_json({"type": "setup_required"})
        await ws.close()
        return ws
    if not await authenticate(ws, request):
        await ws.close()
        return ws

    print(f"Phone connected: {request.remote}")
    await ws.send_json({
        "type": "hello",
        "platform": "mac" if IS_MAC else "pc",
        "liveSlides": win32com is not None,
    })
    await ws.send_json({"type": "slide", "info": request.app["slide"]})
    request.app["sockets"].add(ws)

    try:
        await read_messages(ws)
    finally:
        request.app["sockets"].discard(ws)

    print(f"Phone disconnected: {request.remote}")
    return ws


async def read_messages(ws):
    async for msg in ws:
        if msg.type != WSMsgType.TEXT:
            continue
        try:
            handle_message(json.loads(msg.data))
        except Exception as exc:  # one bad message shouldn't drop the connection
            print(f"Ignored message {msg.data!r}: {exc}")


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return False
        except OSError:
            return True


def main():
    # Packaged apps without a console (the Mac .app) have no stdout to print to.
    if sys.stdout is None:
        sys.stdout = sys.stderr = open(os.devnull, "w")

    parser = argparse.ArgumentParser(description="Use your phone as a presentation clicker.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="don't open the QR page on the laptop")
    parser.add_argument("--version", action="version", version=f"Phone Clicker {__version__}")
    args = parser.parse_args()

    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("Phone Clicker")

    # Launched a second time (e.g. from the Start menu): just show the running one's QR page.
    if port_in_use(args.port):
        print(f"Phone Clicker is already running on port {args.port}. Opening its QR page.")
        webbrowser.open(f"http://localhost:{args.port}/connect")
        return

    token = secrets.token_urlsafe(24)  # 192 random bits
    phone_url = f"http://{get_lan_ip()}:{args.port}/?t={token}"

    app = web.Application()
    app["token"] = token
    app["phone_url"] = phone_url
    app["sockets"] = set()
    app["slide"] = None
    app["passcode"] = Passcode()
    app["guard"] = Guard()
    app["devices"] = {}  # device id -> key, for phones that already unlocked this run
    app.add_routes([
        web.get("/", index),
        web.get("/connect", connect_page),
        web.get("/api/status", api_status),
        web.get("/api/qr", api_qr),
        web.post("/api/passcode", api_passcode),
        web.get("/ws", websocket),
        web.post("/quit", quit_app),
        web.static("/static", STATIC_DIR),
    ])

    # The terminal QR code uses block characters, which older Windows consoles can't print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(f"\nPhone Clicker {__version__}\n")
    if args.no_browser:
        if not app["passcode"].is_set:
            print(f"Set a passcode first: open http://localhost:{args.port}/connect on this laptop.\n")
        else:
            qr = qrcode.QRCode(border=1)
            qr.add_data(phone_url)
            print("Scan this with your phone (same Wi-Fi as this laptop):\n")
            qr.print_ascii(invert=True)
            print(f"\nOr open: {phone_url}\n")
    else:
        # The QR code stays off this window, which could be on a projector. The browser page
        # has the safeguards (passcode setup, hiding the QR while another screen is connected).
        print(f"The QR code is in your browser: http://localhost:{args.port}/connect\n")

    async def open_browser(_app):
        if not args.no_browser:
            webbrowser.open(f"http://localhost:{args.port}/connect")

    app.on_startup.append(open_browser)

    if win32com is not None:
        watcher = PowerPointWatcher()

        async def start_watcher(app):
            app["watcher_task"] = asyncio.create_task(watcher.watch(app))

        async def stop_watcher(app):
            app["watcher_task"].cancel()

        app.on_startup.append(start_watcher)
        app.on_cleanup.append(stop_watcher)

    web.run_app(app, host="0.0.0.0", port=args.port, print=lambda *_: print("Close this window to stop.\n"))


if __name__ == "__main__":
    main()
