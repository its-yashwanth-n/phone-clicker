// Phone Clicker remote: sends button presses and touch gestures to the laptop.

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const profileSelect = $("#profile");

// Take the access token out of the address bar so it doesn't show up in screenshots or
// history. It's kept in sessionStorage so refreshing the page still works.
const token = (() => {
  const fromUrl = new URLSearchParams(location.search).get("t");
  try {
    if (fromUrl) {
      sessionStorage.setItem("token", fromUrl);
      history.replaceState(null, "", location.pathname);
      return fromUrl;
    }
    return sessionStorage.getItem("token") || "";
  } catch {
    return fromUrl || "";
  }
})();

function load(key, fallback) {
  try { return { ...fallback, ...JSON.parse(localStorage.getItem(key)) }; } catch { return { ...fallback }; }
}
function save(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
}

// ---------- Settings ----------

const DEFAULT_SETTINGS = {
  theme: "auto",
  accent: "blue",
  nextSize: "medium",
  haptics: true,
  swipe: true,
  confirmEnd: false,
  showCounter: true,
  showExtras: true,
  showTimer: true,
  timerTarget: 0,
  padSpeed: 1.8,
  scrollSpeed: 1,
  naturalScroll: true,
};
let settings = load("settings", DEFAULT_SETTINGS);

function applySettings() {
  const root = document.documentElement;
  root.dataset.theme = settings.theme;
  root.dataset.accent = settings.accent;
  root.dataset.nextSize = settings.nextSize;
  $("#timer").classList.toggle("hidden", !settings.showTimer);
  $("#next-hint").textContent = settings.swipe ? "tap · swipe ← next · swipe → back" : "tap for next slide";
  applyProfile();
  timer.render();
}

function syncSettingsForm() {
  $$("#settings-dialog [data-setting]").forEach((el) => {
    const value = settings[el.dataset.setting];
    if (el.classList.contains("segmented") || el.classList.contains("swatches")) {
      el.querySelectorAll("button").forEach((b) => b.classList.toggle("selected", b.dataset.value === value));
    } else if (el.type === "checkbox") {
      el.checked = value;
    } else {
      el.value = value;
    }
  });
}

function setSetting(name, value) {
  settings[name] = value;
  save("settings", settings);
  syncSettingsForm();
  applySettings();
}

$$("#settings-dialog [data-setting]").forEach((el) => {
  const name = el.dataset.setting;
  if (el.classList.contains("segmented") || el.classList.contains("swatches")) {
    el.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => setSetting(name, b.dataset.value)));
  } else if (el.type === "checkbox") {
    el.addEventListener("change", () => setSetting(name, el.checked));
  } else {
    el.addEventListener("input", () => {
      const n = parseFloat(el.value);
      if (!Number.isNaN(n)) setSetting(name, n);
    });
  }
});

$("#reset-settings").addEventListener("click", () => {
  settings = { ...DEFAULT_SETTINGS };
  save("settings", settings);
  syncSettingsForm();
  applySettings();
});

// ---------- Dialogs ----------

const settingsDialog = $("#settings-dialog");
const slideDialog = $("#slide-dialog");

$("#open-settings").addEventListener("click", () => {
  syncSettingsForm();
  settingsDialog.showModal();
});

// Tapping the dimmed backdrop closes a dialog.
[settingsDialog, slideDialog].forEach((dialog) => {
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
});

// ---------- Connection ----------

let ws;
let platform = "pc";
let liveSlides = false;
let authed = false;

function setConnected(on) {
  $("#conn").classList.toggle("on", on);
  $("#conn-text").textContent = on ? `Connected to ${platform === "mac" ? "Mac" : "PC"}` : "Reconnecting…";
  document.body.classList.toggle("offline", !on);
}

// After the first unlock, the phone and laptop both derive a device key from the login (it is
// never sent). Reconnecting (refresh, screen lock, Wi-Fi blip) signs a fresh nonce with it
// instead of asking for the passcode again. It only works until the laptop app restarts.
function savedDevice() {
  try {
    const d = JSON.parse(localStorage.getItem("device"));
    return d && d.token === token && d.id && d.key ? d : null;
  } catch { return null; }
}
function saveDevice(device) {
  try { localStorage.setItem("device", JSON.stringify(device ? { token, ...device } : null)); } catch {}
}

// The latest challenge from the laptop: SRP values for a passcode attempt plus a nonce.
let challenge = null;
let pendingDeviceKey = null;

function connect() {
  ws = new WebSocket(`ws://${location.host}/ws?t=${encodeURIComponent(token)}`);
  ws.onclose = (event) => {
    authed = false;
    setConnected(false);
    if (event.code === 4001) {
      saveDevice(null);
      lock.show("enter", "The passcode was changed on the laptop. Enter the new one.");
    } else if (!savedDevice() && lock.state !== "setup") {
      lock.show("connecting");
    }
    setTimeout(connect, lock.state === "setup" ? 3000 : 1000);
  };
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.B) challenge = msg; // every retry message carries a fresh challenge
    if (msg.type === "challenge") {
      const device = savedDevice();
      if (device) {
        const proof = PhoneClickerCrypto.deviceProof(device.key, msg.nonce);
        ws.send(JSON.stringify({ type: "auth", device: device.id, proof }));
      } else if (lock.state !== "locked") {
        lock.show("enter");
      }
    } else if (msg.type === "auth_required") {
      saveDevice(null);
      if (lock.state !== "locked") lock.show("enter");
    } else if (msg.type === "auth_ok") {
      authed = true;
      if (pendingDeviceKey) saveDevice({ id: msg.device, key: pendingDeviceKey });
      pendingDeviceKey = null;
      lock.hide();
    } else if (msg.type === "auth_fail") {
      lock.wrong(msg.remaining);
    } else if (msg.type === "locked") {
      lock.lockout(msg.seconds);
    } else if (msg.type === "setup_required") {
      lock.show("setup");
    } else if (msg.type === "hello") {
      platform = msg.platform;
      liveSlides = msg.liveSlides;
      if (platform !== "mac") $$("[data-mac-only]").forEach((el) => el.remove());
      $("#about-text").textContent =
        `Connected to a ${platform === "mac" ? "Mac" : "Windows PC"}. ` +
        (liveSlides
          ? "Live slide numbers from PowerPoint are available."
          : "Slide numbers are counted on the phone.");
      setConnected(true);
      applyProfile();
    } else if (msg.type === "slide") {
      slides.live = msg.info;
      slides.render();
    }
  };
}

function send(msg) {
  if (authed && ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
}

// ---------- Passcode lock screen ----------

const lock = {
  el: $("#lock"),
  state: "connecting",
  code: "",
  countdown: null,

  show(state, message) {
    this.state = state;
    this.el.classList.remove("unlocked");
    clearInterval(this.countdown);
    const texts = {
      connecting: ["Connecting…", "Looking for your laptop."],
      enter: ["Enter passcode", "Type the passcode you set on your laptop."],
      setup: ["Finish setup on your laptop", "Create a passcode on the Phone Clicker page on your laptop. This screen updates by itself."],
    };
    const [title, msg] = texts[state] || texts.connecting;
    $("#lock-title").textContent = title;
    this.message(message || msg, Boolean(message) && state === "enter");
    $("#keypad").classList.toggle("hidden", state !== "enter" && state !== "locked");
    $("#keypad").classList.toggle("disabled", state === "locked");
    $("#dots").classList.toggle("hidden", state !== "enter" && state !== "locked");
    this.setCode("");
  },

  hide() {
    this.state = "unlocked";
    clearInterval(this.countdown);
    this.setCode("");
    this.el.classList.add("unlocked");
  },

  message(text, isError = false) {
    $("#lock-msg").textContent = text;
    $("#lock-msg").classList.toggle("error", isError);
  },

  setCode(code) {
    this.code = code;
    const slots = Math.max(4, code.length);
    $("#dots").innerHTML = Array.from({ length: slots }, (_, i) => `<span class="${i < code.length ? "filled" : ""}"></span>`).join("");
    $("#key-ok").disabled = code.length < 4;
  },

  press(digit) {
    if (this.state === "enter" && this.code.length < 8) {
      this.setCode(this.code + digit);
      buzz(8);
    }
  },

  submit() {
    if (this.state !== "enter" || this.code.length < 4 || !challenge) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const code = this.code;
    this.state = "checking";
    this.setCode("");
    $("#keypad").classList.add("disabled");
    this.message("Checking…");
    // Let the screen update before the (deliberately slow) key derivation runs.
    setTimeout(() => {
      try {
        // The passcode never leaves the phone: only an SRP proof is sent.
        const { A, M1, deviceKey } = PhoneClickerCrypto.srpLogin(code, challenge);
        pendingDeviceKey = deviceKey;
        ws.send(JSON.stringify({ type: "auth", A, M1 }));
      } catch {
        this.show("enter", "Something went wrong. Please try again.");
      }
    }, 30);
  },

  wrong(remaining) {
    this.show("enter", `Wrong passcode. ${remaining} ${remaining === 1 ? "try" : "tries"} left before a short lockout.`);
    const dots = $("#dots");
    dots.classList.remove("shake");
    void dots.offsetWidth; // restart the animation
    dots.classList.add("shake");
    if (navigator.vibrate) navigator.vibrate([60, 40, 60]);
  },

  lockout(seconds) {
    this.show("locked");
    $("#lock-title").textContent = "Too many wrong tries";
    const until = Date.now() + seconds * 1000;
    const tick = () => {
      const left = Math.ceil((until - Date.now()) / 1000);
      if (left <= 0) return this.show("enter");
      this.message(`For your security, try again in ${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}.`, true);
    };
    tick();
    this.countdown = setInterval(tick, 500);
  },
};

$$("#keypad [data-digit]").forEach((b) => b.addEventListener("click", () => lock.press(b.dataset.digit)));
$("#key-del").addEventListener("click", () => lock.setCode(lock.code.slice(0, -1)));
$("#key-ok").addEventListener("click", () => lock.submit());
// A hardware keyboard works too (handy when testing on a computer).
document.addEventListener("keydown", (e) => {
  if (lock.state !== "enter") return;
  if (/^\d$/.test(e.key)) lock.press(e.key);
  else if (e.key === "Backspace") lock.setCode(lock.code.slice(0, -1));
  else if (e.key === "Enter") lock.submit();
});

function buzz(ms = 15) {
  if (settings.haptics && navigator.vibrate) navigator.vibrate(ms);
}

function pressKey(action) {
  send({ type: "key", action, profile: profileSelect.value });
  buzz();
  slides.onAction(action);
  if (action === "start" || action === "start_here") timer.start();
}

// ---------- Slide counter ----------

const slides = {
  counter: load("counter", { current: 1, total: 0 }),
  live: null, // { mode, current, total } read from PowerPoint by the laptop

  usingLive() {
    return this.live && profileSelect.value === "powerpoint";
  },

  onAction(action) {
    const c = this.counter;
    if (action === "next") c.current = c.total ? Math.min(c.current + 1, c.total) : c.current + 1;
    else if (action === "prev") c.current = Math.max(1, c.current - 1);
    else if (action === "start" || action === "first") c.current = 1;
    else if (action === "last" && c.total) c.current = c.total;
    else return;
    save("counter", c);
    this.render();
  },

  render() {
    const live = this.usingLive();
    const { current, total } = live ? this.live : this.counter;
    $("#slide-kind").textContent = profileSelect.value === "pdf" ? "Page" : "Slide";
    $("#slide-num").textContent = current;
    $("#slide-total").textContent = total ? `/ ${total}` : "";
    $("#progress-bar").style.width = total ? `${Math.min(100, (current / total) * 100)}%` : "0";

    const badge = $("#slide-badge");
    badge.classList.toggle("live", Boolean(live));
    badge.textContent = live ? (this.live.mode === "show" ? "LIVE" : "EDITING") : "TAP TO SET";
  },
};

$("#slide-info").addEventListener("click", () => {
  const live = slides.usingLive();
  $("#slide-dialog-note").textContent = live
    ? "This number comes straight from PowerPoint on your laptop, so it's always right. The fields below set the phone's own counter, which is used for other apps."
    : "The phone counts your taps on Next and Previous. Animations count as taps too, so correct the number here if it drifts.";
  $("#set-current").value = slides.counter.current;
  $("#set-total").value = slides.counter.total || "";
  slideDialog.showModal();
});

$$("[data-step]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const input = $("#set-current");
    input.value = Math.max(1, (parseInt(input.value, 10) || 1) + parseInt(btn.dataset.step, 10));
  });
});
$("#slide-reset").addEventListener("click", () => { $("#set-current").value = 1; });

slideDialog.addEventListener("close", () => {
  const total = Math.max(0, parseInt($("#set-total").value, 10) || 0);
  let current = Math.max(1, parseInt($("#set-current").value, 10) || 1);
  if (total) current = Math.min(current, total);
  slides.counter = { current, total };
  save("counter", slides.counter);
  slides.render();
});

// ---------- Tabs and profile ----------

$$(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".tabs button").forEach((b) => b.classList.toggle("active", b === btn));
    $$(".tab").forEach((t) => t.classList.toggle("active", t.id === `tab-${btn.dataset.tab}`));
  });
});

// Apps that have no "start from current slide" shortcut, per laptop platform.
const NO_START_HERE = { pc: ["powerpoint_web"], mac: ["keynote"] };

function applyProfile() {
  const p = profileSelect.value;
  const isPdf = p === "pdf";
  $("#slide-extras").classList.toggle("hidden", isPdf || !settings.showExtras);
  $("#pdf-extras").classList.toggle("hidden", !isPdf || !settings.showExtras);
  $("#slide-info").classList.toggle("hidden", !settings.showCounter);
  $("#start-here").textContent = isPdf ? "Full (F11)" : "From here";
  $("#start-here").classList.toggle("hidden", (NO_START_HERE[platform] || []).includes(p));
  try { localStorage.setItem("profile", p); } catch {}
  slides.render();
}

try {
  const saved = localStorage.getItem("profile");
  if (saved) profileSelect.value = saved;
} catch {}
profileSelect.addEventListener("change", applyProfile);

// Any button with data-action sends that action.
$$("[data-action]").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (btn.id === "end-show") {
      if (settings.confirmEnd && !confirm("End the slideshow?")) return;
      timer.pause();
    }
    pressKey(btn.dataset.action);
  });
});

// ---------- Big NEXT button: tap = next, swipe left = next, swipe right = previous ----------

const nextBtn = $("#next");
let swipeStart = null;
nextBtn.addEventListener("pointerdown", (e) => {
  swipeStart = { x: e.clientX, y: e.clientY };
  nextBtn.classList.add("pressed");
});
nextBtn.addEventListener("pointerup", (e) => {
  nextBtn.classList.remove("pressed");
  if (!swipeStart) return;
  const dx = e.clientX - swipeStart.x;
  swipeStart = null;
  pressKey(settings.swipe && dx > 60 ? "prev" : "next");
});
nextBtn.addEventListener("pointercancel", () => {
  nextBtn.classList.remove("pressed");
  swipeStart = null;
});

// ---------- Timer ----------

const fmt = (ms) => {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};

const timer = {
  el: $("#timer"),
  elapsed: 0,
  startedAt: null,
  interval: null,
  buzzed: false,
  start() {
    if (this.startedAt) return;
    this.startedAt = Date.now();
    this.interval = setInterval(() => this.render(), 500);
    this.render();
  },
  pause() {
    if (!this.startedAt) return;
    this.elapsed += Date.now() - this.startedAt;
    this.startedAt = null;
    clearInterval(this.interval);
    this.render();
  },
  reset() {
    this.pause();
    this.elapsed = 0;
    this.buzzed = false;
    this.render();
  },
  render() {
    const ms = this.elapsed + (this.startedAt ? Date.now() - this.startedAt : 0);
    const target = settings.timerTarget * 60000;
    let text = fmt(ms);
    let state = "";
    if (target) {
      // Count down to the talk length, then count overtime with a "+".
      const left = target - ms;
      text = left > 0 ? fmt(left + 999) : `+${fmt(-left)}`;
      if (left <= 0) state = "over";
      else if (left <= 120000) state = "warn";
      if (left <= 0 && !this.buzzed && this.startedAt) {
        this.buzzed = true;
        if (navigator.vibrate) navigator.vibrate([300, 150, 300]);
      }
    }
    this.el.textContent = text;
    this.el.classList.toggle("running", Boolean(this.startedAt) && !state);
    this.el.classList.toggle("warn", state === "warn");
    this.el.classList.toggle("over", state === "over");
  },
};
timer.el.addEventListener("click", () => (timer.startedAt ? timer.pause() : timer.start()));
timer.el.addEventListener("dblclick", () => timer.reset());

// ---------- Touchpad ----------

const pad = $("#pad");
const pointers = new Map();
let gesture = null; // { start, maxPointers, moved }
let pendingMove = { x: 0, y: 0 };
let scrollAccum = 0;
let frameQueued = false;

function flushMove() {
  frameQueued = false;
  const dx = Math.trunc(pendingMove.x);
  const dy = Math.trunc(pendingMove.y);
  if (dx || dy) {
    send({ type: "move", dx, dy });
    pendingMove.x -= dx;
    pendingMove.y -= dy;
  }
}

pad.addEventListener("pointerdown", (e) => {
  pad.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (!gesture) gesture = { start: Date.now(), maxPointers: 0, moved: 0 };
  gesture.maxPointers = Math.max(gesture.maxPointers, pointers.size);
});

pad.addEventListener("pointermove", (e) => {
  const prev = pointers.get(e.pointerId);
  if (!prev) return;
  const dx = e.clientX - prev.x;
  const dy = e.clientY - prev.y;
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  gesture.moved += Math.abs(dx) + Math.abs(dy);

  if (pointers.size === 1) {
    pendingMove.x += dx * settings.padSpeed;
    pendingMove.y += dy * settings.padSpeed;
    if (!frameQueued) {
      frameQueued = true;
      requestAnimationFrame(flushMove);
    }
  } else if (pointers.size === 2) {
    // Average the two fingers by halving each finger's contribution.
    scrollAccum += (dy / 2) * (settings.naturalScroll ? 1 : -1);
    const stepSize = 20 / settings.scrollSpeed;
    const steps = Math.trunc(scrollAccum / stepSize);
    if (steps) {
      send({ type: "scroll", dy: steps });
      scrollAccum -= steps * stepSize;
    }
  }
});

function endPointer(e) {
  pointers.delete(e.pointerId);
  if (pointers.size || !gesture) return;
  const isTap = Date.now() - gesture.start < 250 && gesture.moved < 10;
  if (isTap) {
    send({ type: "click", button: gesture.maxPointers >= 2 ? "right" : "left" });
    buzz(10);
  }
  gesture = null;
  scrollAccum = 0;
}
pad.addEventListener("pointerup", endPointer);
pad.addEventListener("pointercancel", endPointer);

$("#left-click").addEventListener("click", () => { send({ type: "click", button: "left" }); buzz(); });
$("#right-click").addEventListener("click", () => { send({ type: "click", button: "right" }); buzz(); });

// ---------- Keyboard ----------

$("#send-text").addEventListener("click", () => {
  const box = $("#text");
  if (!box.value) return;
  send({ type: "text", text: box.value });
  box.value = "";
  buzz();
});

// Keep the phone screen awake where the browser allows it (needs HTTPS on most browsers).
async function keepAwake() {
  try { await navigator.wakeLock?.request("screen"); } catch {}
}
document.addEventListener("visibilitychange", () => document.visibilityState === "visible" && keepAwake());
keepAwake();

applySettings();
setConnected(false);
connect();
