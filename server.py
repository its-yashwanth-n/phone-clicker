"""Phone Clicker - use your phone as a presentation remote.

Run this on your laptop, scan the QR code with your phone, and the phone
becomes a clicker for PowerPoint, Google Slides, PDFs, media and more.
Key presses are sent to whichever window is focused on the laptop.
"""

import argparse
import asyncio
import io
import json
import secrets
import socket
import sys
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

STATIC_DIR = Path(__file__).parent / "static"
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


def is_local(request):
    return request.remote in ("127.0.0.1", "::1")


async def index(request):
    return web.FileResponse(STATIC_DIR / "index.html")


async def connect_page(request):
    # Shows the QR code on the laptop. Only reachable from the laptop itself,
    # since the URL contains the access token.
    if not is_local(request):
        raise web.HTTPForbidden()
    url = request.app["phone_url"]
    buf = io.BytesIO()
    qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12).save(buf)
    svg = buf.getvalue().decode()
    html = (STATIC_DIR / "connect.html").read_text(encoding="utf-8")
    return web.Response(
        text=html.replace("{{QR}}", svg).replace("{{URL}}", url),
        content_type="text/html",
    )


async def websocket(request):
    if not secrets.compare_digest(request.query.get("t", ""), request.app["token"]):
        raise web.HTTPForbidden()

    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
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


def main():
    parser = argparse.ArgumentParser(description="Use your phone as a presentation clicker.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="don't open the QR page on the laptop")
    args = parser.parse_args()

    token = secrets.token_urlsafe(8)
    phone_url = f"http://{get_lan_ip()}:{args.port}/?t={token}"

    app = web.Application()
    app["token"] = token
    app["phone_url"] = phone_url
    app["sockets"] = set()
    app["slide"] = None
    app.add_routes([
        web.get("/", index),
        web.get("/connect", connect_page),
        web.get("/ws", websocket),
        web.static("/static", STATIC_DIR),
    ])

    # The terminal QR code uses block characters, which older Windows consoles can't print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    qr = qrcode.QRCode(border=1)
    qr.add_data(phone_url)
    print("\nScan this with your phone (same Wi-Fi as this laptop):\n")
    qr.print_ascii(invert=True)
    print(f"\nOr open: {phone_url}\n")

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
    web.run_app(app, host="0.0.0.0", port=args.port, print=lambda *_: print("Press Ctrl+C to stop.\n"))


if __name__ == "__main__":
    main()
