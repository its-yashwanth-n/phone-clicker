# 📱 Phone Clicker

**Turn your phone into a wireless presentation clicker.** Control PowerPoint, Google Slides, Keynote, PDFs, videos and more from your phone. You don't install anything on the phone.

```
 ┌──────────────┐        same Wi-Fi         ┌──────────────────┐
 │    Phone     │   --------------------->  │    Laptop        |
 │  (browser)   │      tap NEXT → → →       │  PowerPoint, PDF │
 └──────────────┘                           └──────────────────┘
```

You install a small app on your laptop. It shows a QR code, you scan it with your phone, and your phone's browser becomes the remote.

<p align="center">
  <img src="docs/screenshots/slides.png" width="200" alt="Slides tab">
  <img src="docs/screenshots/settings.png" width="200" alt="Settings">
  <img src="docs/screenshots/slides-light-pdf.png" width="200" alt="Light theme in PDF mode">
</p>

📖 **New here? Read the [full user guide (PDF)](docs/Phone-Clicker-User-Guide.pdf)**. It explains every screen and button with pictures.

---

## Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Running it](#-running-it)
- [Using it](#-using-it)
- [Troubleshooting](#-troubleshooting)
- [Security and passcode](#-security-and-passcode)
- [How it works](#-how-it-works)
- [Running from source](#-running-from-source)

---

## ✨ Features

| | |
|---|---|
| 🎯 **Slide control** | A big NEXT button (tap it or swipe), Previous, Start, Start from current slide, End |
| 🖥️ **Works with your app** | PowerPoint (desktop and web), Google Slides, Keynote and PDF viewers |
| 🔢 **Slide number** | See which slide you're on. It's read live from PowerPoint on Windows and counted on the phone for other apps |
| ⬛ **Presenter tricks** | Black or white screen, jump to the first or last slide, a countdown timer for your talk |
| 🖱️ **Touchpad** | Use your phone as a wireless mouse, with scrolling and right-click |
| 🎵 **Media keys** | Play/pause, next and previous track, volume, mute, full screen |
| ⌨️ **Keyboard** | Type on your phone and the text appears on the laptop |
| ⚙️ **Settings** | Dark or light theme, accent colors, NEXT button size, vibration, swipe, timer and touchpad speed |
| 🔒 **Secure** | 4–8 digit passcode, lockout after wrong tries, and the QR code hides itself while a projector is connected |
| 📲 **No phone app** | Works in any phone browser (Chrome, Safari, Firefox, Samsung Internet) |

---

## 📋 Requirements

- A **laptop** running Windows 10/11 (64-bit), macOS 12+ on Apple Silicon, or Linux (X11)
- A **phone** with a web browser and a camera to scan the QR code
- The phone and laptop on the **same Wi-Fi network** (a phone hotspot works too)

You **don't need Python** or anything else. The app comes with everything built in.

---

## 📥 Installation

Download the file for your laptop from the **[latest release](https://github.com/its-yashwanth-n/phone-clicker/releases/latest)**:

| Laptop | Download | What it is |
|---|---|---|
| 🪟 **Windows** | `PhoneClicker-Setup-x.y.z.exe` | Installer (recommended) |
| 🪟 Windows, no install | `PhoneClicker-x.y.z-windows-portable.zip` | Unzip and run `PhoneClicker.exe`, e.g. from a USB stick |
| 🍎 **Mac** (M1/M2/M3/M4) | `PhoneClicker-x.y.z-macos-apple-silicon.dmg` | Drag-to-Applications disk image |
| 🐧 **Linux** | `PhoneClicker-x.y.z-linux-x64.tar.gz` | Unpack and run `PhoneClicker/PhoneClicker` |

### 🪟 Windows

1. Run **`PhoneClicker-Setup-x.y.z.exe`**.
2. Windows may show **"Windows protected your PC"**. That's because the app isn't code-signed yet. Click **More info → Run anyway**.
3. Click through the installer. It doesn't need admin rights, and you can tick **Create a desktop shortcut**.

To uninstall, go to **Settings → Apps → Installed apps → Phone Clicker → Uninstall**.

### 🍎 Mac

1. Open the **`.dmg`** and drag **Phone Clicker** into **Applications**.
2. The first time you open it, macOS says it "can't be opened" because the app isn't notarized. Go to **System Settings → Privacy & Security**, scroll down and click **Open Anyway**. On older macOS versions, right-click the app and choose **Open** instead.
3. Allow it to press keys: in **System Settings → Privacy & Security → Accessibility**, turn on **Phone Clicker**.

To uninstall, drag Phone Clicker from Applications to the Bin.

### 🐧 Linux

```bash
tar -xzf PhoneClicker-*-linux-x64.tar.gz
./PhoneClicker/PhoneClicker
```

You need an **X11** session. Wayland blocks programs from pressing keys.

> 💻 Intel Mac, or want to run the Python code yourself? See [Running from source](#-running-from-source).

---

## ▶️ Running it

Open **Phone Clicker** from the Start menu, your desktop shortcut, or the Applications folder.

> **The first time on Windows, the firewall asks about Phone Clicker. Tick "Private networks" and click Allow.** If you skip this, your phone won't be able to connect.

A page opens in your browser on the laptop.

### First time: create a passcode

<p align="center">
  <img src="docs/screenshots/laptop-setup.png" width="360" alt="Create a passcode on the laptop">
</p>

The first time, you choose a **4–8 digit passcode**. Phones have to type it before they can control your laptop. You can **only set it on the laptop**, never from a phone. After that, the page shows the QR code.

On Windows and Linux, a small console window also opens. It only shows a status message, never the QR code, because that window could end up on a projector.

**To stop it:**
- **Windows / Linux:** close the console window.
- **Any laptop:** click **Stop Phone Clicker** on the QR page.

If you open Phone Clicker again while it's already running, it just shows the QR page again.

---

## 🎤 Using it

### Connect your phone

1. Open your phone's **camera** and point it at the QR code.
2. Tap the link that pops up.
3. **Type your passcode** on the keypad and tap ✓.
4. Check that the **dot in the top-left corner is green**. That means you're connected.

> 💡 **Tip:** the link changes every time you restart Phone Clicker, so scan the QR code again after a restart. While the app keeps running, refreshing the page or locking your phone won't ask for the passcode again.

---

## 🔒 Security and passcode

Phone Clicker can press keys on your laptop, so it's locked down:

| Protection | What it does |
|---|---|
| 🔢 **Passcode** | Every phone must enter your 4–8 digit passcode before it can do anything. Easy codes like `1234` or `0000` are refused |
| 💻 **Set on the laptop only** | You can only create or change the passcode on the laptop's own page. Phones and other websites are blocked from it. Changing it needs the current passcode, and logs out every connected phone |
| 🚫 **Lockout** | After 5 wrong tries, that phone is locked out for 30 seconds, then 1 min, 2 min... up to 15 min. 20 wrong tries from anywhere locks everyone out for 5 minutes |
| 🤐 **Passcode never sent** | The phone proves it knows the passcode with [SRP](https://datatracker.ietf.org/doc/html/rfc5054), a challenge-response protocol. The passcode never crosses the Wi-Fi, and recorded traffic can't be used to guess it offline. Every guess has to go to the laptop, where the lockout applies |
| 🔁 **No replays** | Each login and reconnect answers a fresh random challenge, so a recorded message is useless later. The reconnect key is worked out on both sides and never transmitted |
| 🔗 **Secret link** | The QR link contains a 192-bit random token that changes on every start. The phone removes it from the address bar after it opens |
| 🧂 **Passcode not stored** | Only an SRP verifier (derived with salted PBKDF2-SHA256) is saved in your user settings folder. The digits themselves are never saved |

> ⚠️ **Limits:** after you unlock, button presses travel unencrypted. Someone on the same Wi-Fi could see *which* buttons you press, but can't take control or learn your passcode. A skilled attacker who actively intercepts traffic on the network (a "man in the middle") could still interfere. Use your own Wi-Fi or your phone's hotspot for important talks.

### Projector and second-screen safety

When you present, your laptop screen may be mirrored to a projector. Phone Clicker watches for that:

<p align="center">
  <img src="docs/screenshots/laptop-setup-warning.png" width="300" alt="Warning when another screen is connected">
  <img src="docs/screenshots/laptop-qr-hidden.png" width="300" alt="QR code hidden after a phone connects">
</p>

- **Another screen detected:** when a projector, TV or monitor is plugged in, the page shows a warning. The passcode form stays hidden until you click *"No one else can see my screen — continue"*.
- **QR code hidden:** the QR code is blurred while another screen is connected, and as soon as a phone connects. Click **Show QR code** to reveal it. It hides itself again after a minute.
- **Passcode is never shown:** it's typed into masked fields on the laptop, and shows only as dots on the phone.
- **Nothing in the console:** the console window never shows the QR code or link.

> 💡 Best practice: switch your display to **Extend** instead of **Duplicate** (<kbd>Win</kbd>+<kbd>P</kbd> on Windows, *System Settings → Displays* on Mac). Keep the Phone Clicker page on your laptop screen.

### Forgot your passcode?

Close Phone Clicker and delete its settings file. Next time you start it, you'll be asked to create a new passcode:

| Laptop | Settings file |
|---|---|
| Windows | `%APPDATA%\PhoneClicker\config.json` |
| Mac | `~/Library/Application Support/PhoneClicker/config.json` |
| Linux | `~/.config/phone-clicker/config.json` |

### Give a presentation

1. On the laptop, **open your presentation** and **click on it once** so it's the active window.
2. On the phone, **choose your app** from the dropdown at the top (for example *PowerPoint (app)*).
3. Tap **▶ Start**. The slideshow starts and the timer begins.
4. Tap the big **NEXT** button to go forward. You can also swipe left on it, or swipe right to go back.
5. Tap **■ End** when you're done.

> ⚠️ Phone Clicker sends key presses to **whichever window is active** on the laptop. If nothing happens, click on your presentation once.

### The four tabs at a glance

| Tab | What it's for | Use it when... |
|---|---|---|
| 🎯 **Slides** | Start, move through and end a slideshow. Shows the slide number and a timer | You're presenting slides or a PDF. This is the tab you'll use 90% of the time |
| 🖱️ **Touchpad** | Turns your phone into a wireless mouse (drag, tap, scroll, right-click) | You need to click a link, play an embedded video or open a file mid-talk |
| 🎵 **Media** | Play/pause, volume, full screen, zoom, switch app, arrow keys | You're showing a YouTube video, playing music, or zooming into something |
| ⌨️ **Keyboard** | Type on your phone and the text appears on the laptop | You need to search, type a URL or fill in a box without walking to the laptop |

#### Slide number

The card above NEXT shows **Slide 4 / 12** and a progress bar.

- **PowerPoint on Windows:** the number is read **live** from PowerPoint (green **LIVE** badge), so it's always right, even with animations.
- **Every other app:** the phone counts your taps. Tap the card to set the current slide or the total number of slides.

#### Settings ⚙️

Tap the gear icon in the top-right corner to change:

- **Appearance:** dark, light or auto theme, five accent colors, and the NEXT button size (S, M or L)
- **Controls:** vibration, swipe gestures, ask before ending, and show or hide the slide counter and the extra buttons
- **Timer:** set a talk length and the timer counts down, turns orange in the last 2 minutes, and turns red with a buzz when time is up
- **Touchpad:** pointer speed, scroll speed and natural scrolling

Your settings are saved on your phone.

> 📖 **Want every button explained?** Read the full **[Phone Clicker User Guide (PDF)](docs/Phone-Clicker-User-Guide.pdf)**.

### App guide

Choose the matching app in the dropdown so **Start** sends the right shortcut:

| App | How to set it up | Start | From here |
|---|---|---|---|
| **PowerPoint (app)** | Open the .pptx file | F5 · ⌘⇧↩ on Mac | Shift+F5 · ⌘↩ on Mac |
| **PowerPoint (web)** | Open it at office.com in your browser | Ctrl+F5 | – |
| **Google Slides** | Open the deck in your browser | Ctrl+Shift+F5 · ⌘⇧↩ on Mac | Ctrl+F5 · ⌘↩ on Mac |
| **Keynote** (Mac only) | Open the .key file | ⌥⌘P | – |
| **PDF** | Open it in Adobe Acrobat/Reader, Edge, Chrome or Preview | Ctrl+L / ⌘L (Acrobat full screen) | F11 / ⌃⌘F (browser and Preview full screen) |

For PDFs, NEXT and Previous use **Page Down / Page Up**, which works in every PDF viewer.

**Other apps:** Canva, Prezi, reveal.js, image viewers and anything else that moves forward with the arrow keys work too. Pick *PowerPoint (app)* and use NEXT and Previous.

---

## 🛠️ Troubleshooting

<details>
<summary><b>My phone can't open the page or the dot stays red</b></summary>

- Make sure the phone and laptop are on the **same Wi-Fi**. Turn off mobile data on the phone to be sure.
- **Guest, hotel, school and office Wi-Fi** often block devices from talking to each other. Instead, turn on your **phone's hotspot** and connect the laptop to it.
- **Windows Firewall:** open *Windows Security → Firewall & network protection → Allow an app through firewall*, find **Phone Clicker** (or **Python** if you run from source), and tick **Private**. Also check that your Wi-Fi is set to *Private* rather than *Public* in Windows network settings.
- Make sure the Phone Clicker window is still open on the laptop.

</details>

<details>
<summary><b>The dot is green but nothing happens on the laptop</b></summary>

- Click on your presentation window so it's active. Key presses go to the active window.
- Check that you picked the right app in the dropdown.
- **macOS:** turn on **Phone Clicker** in *System Settings → Privacy & Security → Accessibility*.
- **Linux:** Phone Clicker needs an **X11** session. Wayland blocks programs from sending key presses. Choose "Ubuntu on Xorg" (or similar) on the login screen.

</details>

<details>
<summary><b>"Start" doesn't start the slideshow</b></summary>

Some browsers and apps grab certain shortcuts. Start the slideshow by hand on the laptop, then use NEXT and Previous from your phone. These use plain arrow keys and work everywhere.

</details>

<details>
<summary><b>My phone screen keeps turning off</b></summary>

Browsers only let pages keep the screen awake over HTTPS, so raise your phone's **auto-lock / screen timeout** while you present. When the screen comes back on, the remote reconnects automatically.

</details>

<details>
<summary><b>"python is not recognized" on Windows (running from source)</b></summary>

Python wasn't added to PATH. Run the Python installer again, choose **Modify**, and tick **"Add Python to environment variables"**. Or reinstall it and tick **"Add python.exe to PATH"**.

</details>

<details>
<summary><b>Port already in use</b></summary>

Another program is using port 8765. Close it, or if you're running from source, use `python server.py --port 9000`.

</details>

---

## ⚙️ How it works

```
Phone browser ──WebSocket over Wi-Fi──▶ server.py ──pynput──▶ key presses / mouse on the laptop
```

| File | Purpose |
|---|---|
| `server.py` | Web and WebSocket server ([aiohttp](https://docs.aiohttp.org)) that turns button presses into key presses and mouse movement ([pynput](https://pynput.readthedocs.io)). On Windows it also reads the current slide from PowerPoint ([pywin32](https://github.com/mhammond/pywin32)) |
| `static/index.html`, `app.js`, `style.css` | The phone remote |
| `static/connect.html` | The laptop page: passcode setup, QR code and second-screen warnings |
| `start.bat` / `start.sh` | One-click launchers that set things up on the first run |
| `docs/` | The PDF user guide and screenshots |
| `packaging/` | App icon, PyInstaller build recipe and the Windows installer script |
| `.github/workflows/release.yml` | Builds the installers for every release |

**Security:** see [Security and passcode](#-security-and-passcode). Everything stays on your local network, and nothing goes to the internet.

---

## 🧑‍💻 Running from source

For developers, or Intel Macs. You'll need [Python 3.9+](https://www.python.org/downloads/). On Windows, tick **"Add python.exe to PATH"** in the installer.

```bash
git clone https://github.com/its-yashwanth-n/phone-clicker.git
cd phone-clicker
```

Then double-click **`start.bat`** (Windows) or run **`./start.sh`** (macOS/Linux). The first run sets up a virtual environment and installs the dependencies.

On macOS, give your terminal app Accessibility permission (see the Mac section above).

Options:

```bash
python server.py --port 9000      # use a different port
python server.py --no-browser     # don't open the QR page on the laptop
python server.py --version
```

### Building the app and installers

```bash
pip install -r requirements.txt -r requirements-build.txt
pyinstaller --noconfirm packaging/phone-clicker.spec
```

This creates `dist/PhoneClicker/` (Windows/Linux) or `dist/Phone Clicker.app` (macOS), with Python bundled inside. You can only build for the operating system you're on.

**Windows installer:** install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then run:

```bash
iscc /DAppVersion=1.0.0 packaging\windows\installer.iss
```

**Icon:** `python packaging/make_icon.py` redraws `packaging/icon.png` and `icon.ico`.

### Publishing a release

Every build is automated with GitHub Actions (`.github/workflows/release.yml`):

1. Bump `__version__` in `server.py`.
2. Commit, then tag and push the version:

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. GitHub builds the Windows installer and portable zip, the Mac `.dmg` and the Linux `.tar.gz`, then publishes them on the Releases page.

You can also run the workflow by hand from the **Actions** tab to test a build without releasing it.

---

## 📄 License

[MIT](LICENSE) © 2026 Yashwanth Nagaraju. Use it, change it and share it freely.
