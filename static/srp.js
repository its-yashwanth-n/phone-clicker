// Phone-side crypto: SHA-256, HMAC, PBKDF2 and the SRP-6a client (RFC 5054).
//
// Browsers only offer their built-in crypto (crypto.subtle) on HTTPS pages. This page is served
// over plain HTTP on the local network, so these are implemented here in plain JavaScript.
// crypto.getRandomValues still works on HTTP and is used for all randomness.
(function (root) {
  "use strict";

  // ---------- SHA-256 ----------

  const K = new Int32Array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]);
  const IV = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const W = new Int32Array(64);

  // Mixes one 64-byte block (16 big-endian words) into the 8-word state, in place.
  function compress(state, block) {
    for (let i = 0; i < 16; i++) W[i] = block[i];
    for (let i = 16; i < 64; i++) {
      const w15 = W[i - 15], w2 = W[i - 2];
      const s0 = ((w15 >>> 7) | (w15 << 25)) ^ ((w15 >>> 18) | (w15 << 14)) ^ (w15 >>> 3);
      const s1 = ((w2 >>> 17) | (w2 << 15)) ^ ((w2 >>> 19) | (w2 << 13)) ^ (w2 >>> 10);
      W[i] = (W[i - 16] + s0 + W[i - 7] + s1) | 0;
    }
    let a = state[0], b = state[1], c = state[2], d = state[3];
    let e = state[4], f = state[5], g = state[6], h = state[7];
    for (let i = 0; i < 64; i++) {
      const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
      const t1 = (h + S1 + ((e & f) ^ (~e & g)) + K[i] + W[i]) | 0;
      const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
      const t2 = (S0 + ((a & b) ^ (a & c) ^ (b & c))) | 0;
      h = g; g = f; f = e; e = (d + t1) | 0;
      d = c; c = b; b = a; a = (t1 + t2) | 0;
    }
    state[0] = (state[0] + a) | 0; state[1] = (state[1] + b) | 0;
    state[2] = (state[2] + c) | 0; state[3] = (state[3] + d) | 0;
    state[4] = (state[4] + e) | 0; state[5] = (state[5] + f) | 0;
    state[6] = (state[6] + g) | 0; state[7] = (state[7] + h) | 0;
  }

  function wordsToBytes(words) {
    const out = new Uint8Array(words.length * 4);
    words.forEach((w, i) => {
      out[i * 4] = w >>> 24; out[i * 4 + 1] = w >>> 16; out[i * 4 + 2] = w >>> 8; out[i * 4 + 3] = w;
    });
    return out;
  }

  // Hashes `bytes`, continuing from `state` which has already absorbed `prefixLen` bytes
  // (a multiple of 64). Used for plain SHA-256 and for HMAC with precomputed key states.
  function finish(state, bytes, prefixLen) {
    const total = prefixLen + bytes.length;
    const padded = new Uint8Array(Math.ceil((bytes.length + 9) / 64) * 64);
    padded.set(bytes);
    padded[bytes.length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(padded.length - 8, Math.floor((total * 8) / 2 ** 32));
    view.setUint32(padded.length - 4, (total * 8) >>> 0);
    const block = new Int32Array(16);
    for (let off = 0; off < padded.length; off += 64) {
      for (let i = 0; i < 16; i++) block[i] = view.getInt32(off + i * 4);
      compress(state, block);
    }
    return wordsToBytes(state);
  }

  function sha256(bytes) {
    return finish(Int32Array.from(IV), bytes, 0);
  }

  // ---------- HMAC and PBKDF2 ----------

  // The inner and outer HMAC states after absorbing the padded key.
  function hmacStates(key) {
    if (key.length > 64) key = sha256(key);
    const pad = (byte) => {
      const block = new Uint8Array(64).fill(byte);
      key.forEach((k, i) => { block[i] ^= k; });
      const view = new DataView(block.buffer);
      const words = new Int32Array(16);
      for (let i = 0; i < 16; i++) words[i] = view.getInt32(i * 4);
      const state = Int32Array.from(IV);
      compress(state, words);
      return state;
    };
    return { inner: pad(0x36), outer: pad(0x5c) };
  }

  function hmac(key, message) {
    const { inner, outer } = hmacStates(key);
    return finish(outer, finish(inner, message, 64), 64);
  }

  // PBKDF2-HMAC-SHA256 with a 32-byte output. Each round reuses the precomputed key states,
  // so it costs two compressions instead of four.
  function pbkdf2(password, salt, iterations) {
    const { inner, outer } = hmacStates(password);
    const first = new Uint8Array(salt.length + 4);
    first.set(salt);
    first[salt.length + 3] = 1; // block index 1, big-endian
    const u1 = hmac(password, first);
    const view = new DataView(u1.buffer);
    const u = new Int32Array(8);
    for (let i = 0; i < 8; i++) u[i] = view.getInt32(i * 4);
    const t = Int32Array.from(u);

    // One block holding a 32-byte message after a 64-byte prefix: total 96 bytes = 768 bits.
    const block = new Int32Array(16);
    block[8] = 0x80000000 | 0;
    block[15] = 768;
    const s = new Int32Array(8);
    for (let n = 1; n < iterations; n++) {
      block.set(u, 0);
      s.set(inner);
      compress(s, block);
      block.set(s, 0);
      u.set(outer);
      compress(u, block);
      for (let i = 0; i < 8; i++) t[i] ^= u[i];
    }
    return wordsToBytes(t);
  }

  // ---------- Helpers ----------

  const utf8 = (text) => new TextEncoder().encode(text);
  const toHex = (bytes) => Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  const fromHex = (hex) => Uint8Array.from(hex.match(/../g) || [], (h) => parseInt(h, 16));
  const toBig = (bytes) => BigInt("0x" + (toHex(bytes) || "0"));
  const concat = (...parts) => {
    const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
    let off = 0;
    for (const p of parts) { out.set(p, off); off += p.length; }
    return out;
  };

  function modPow(base, exp, mod) {
    let result = 1n;
    base %= mod;
    while (exp > 0n) {
      if (exp & 1n) result = (result * base) % mod;
      exp >>= 1n;
      base = (base * base) % mod;
    }
    return result;
  }

  // ---------- SRP-6a client ----------

  const N = BigInt(
    "0xAC6BDB41324A9A9BF166DE5E1389582FAF72B6651987EE07FC3192943DB56050A37329CBB4A099ED8193E0757767A13DD52312AB4B03310D" +
    "CD7F48A9DA04FD50E8083969EDB767B0CF6095179A163AB3661A05FBD5FAAAE82918A9962F0B93B855F97993EC975EEAA80D740ADBF4FF74" +
    "7359D041D5C33EA71D281E446B14773BCA97B43A23FB801676BD207A436C6481F1D2B9078717461A5B9D32E688F87748544523B524B0D57D" +
    "5EA77A2775D2ECFA032CFBDBF52FB3786160279004E57AE6AF874E7303CE53299CCC041C7BC308D82A5698F3A8D0C38271AE35F8E9DBFBB6" +
    "94B5C803D89F7AE435DE236D525F54759B65E372FCD68EF20FA7111F9E4AFF73"
  );
  const g = 2n;
  const pad = (n) => fromHex(n.toString(16).padStart(512, "0"));
  const k = toBig(sha256(concat(pad(N), pad(g))));

  // Proves knowledge of `code` for the laptop's challenge without revealing it.
  // Returns what to send ({A, M1}) and the device key to keep for quick reconnects.
  function srpLogin(code, challenge) {
    const B = BigInt("0x" + challenge.B);
    if (B % N === 0n) throw new Error("bad challenge");
    const x = toBig(pbkdf2(utf8(code), fromHex(challenge.salt), challenge.iterations));
    const a = toBig(crypto.getRandomValues(new Uint8Array(32)));
    const A = modPow(g, a, N);
    const u = toBig(sha256(concat(pad(A), pad(B))));
    if (u === 0n) throw new Error("bad challenge");
    const base = (((B - ((k * modPow(g, x, N)) % N)) % N) + N) % N;
    const S = modPow(base, a + u * x, N);
    const M1 = sha256(concat(pad(A), pad(B), pad(S)));
    const sessionKey = sha256(pad(S));
    return {
      A: A.toString(16),
      M1: toHex(M1),
      deviceKey: toHex(hmac(sessionKey, utf8("phone-clicker-device"))),
    };
  }

  // Signs the laptop's nonce with the saved device key.
  function deviceProof(deviceKeyHex, nonce) {
    return toHex(hmac(fromHex(deviceKeyHex), utf8(nonce)));
  }

  root.PhoneClickerCrypto = { sha256, hmac, pbkdf2, srpLogin, deviceProof, toHex, fromHex, utf8 };
})(typeof window !== "undefined" ? window : globalThis);
