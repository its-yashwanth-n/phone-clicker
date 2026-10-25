# PyInstaller build recipe: bundles Python, the libraries and the phone page into one app.
# Build with:  pyinstaller --noconfirm packaging/phone-clicker.spec
# Output:      dist/PhoneClicker/ (Windows, Linux) or dist/Phone Clicker.app (macOS)

import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
IS_MAC = sys.platform == "darwin"
VERSION = re.search(r'__version__ = "(.+?)"', (ROOT / "server.py").read_text(encoding="utf-8")).group(1)

# pynput picks its keyboard/mouse backend at runtime, so PyInstaller can't see it by itself.
if sys.platform == "win32":
    backends = ["pynput.keyboard._win32", "pynput.mouse._win32"]
elif IS_MAC:
    backends = ["pynput.keyboard._darwin", "pynput.mouse._darwin"]
else:
    backends = ["pynput.keyboard._xorg", "pynput.mouse._xorg"]

a = Analysis(
    [str(ROOT / "server.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "static"), "static")],
    hiddenimports=backends,
    # PIL is only used to draw the icon at build time; qrcode makes SVGs without it.
    excludes=["tkinter", "unittest", "pydoc", "PIL"],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PhoneClicker",
    icon=str(ROOT / "packaging" / ("icon.png" if IS_MAC else "icon.ico")),
    # Windows/Linux keep a console window: it shows the QR code, and closing it stops the app.
    # The Mac app has no console; it's stopped with the button on the QR page.
    console=not IS_MAC,
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="PhoneClicker", upx=False)

if IS_MAC:
    app = BUNDLE(
        coll,
        name="Phone Clicker.app",
        icon=str(ROOT / "packaging" / "icon.png"),
        bundle_identifier="io.github.phoneclicker",
        info_plist={
            "CFBundleName": "Phone Clicker",
            "CFBundleDisplayName": "Phone Clicker",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSApplicationCategoryType": "public.app-category.productivity",
            "NSHighResolutionCapable": True,
        },
    )
