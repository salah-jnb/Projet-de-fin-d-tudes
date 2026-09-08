#!/usr/bin/env python3
"""
Interface web Flask sur Raspberry Pi :
  - aperçu vidéo live (MJPEG via rpicam-vid / libcamera-vid), comme l'ancien script
  - bouton : envoie la dernière image du flux au backend (POST /api/identify-face)
  - affiche le nom ou « inconnu »

La capture utilise le dernier JPEG extrait du flux (évite d'ouvrir la caméra
deux fois : rpicam-still + rpicam-vid en parallèle échoue souvent).

Sur le Pi :
  pip install flask requests
  export FACE_API_BASE=http://192.168.1.103:8000
  python3 face_capture_web.py
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from typing import List, Optional, Tuple

import requests
from flask import Flask, Response, jsonify, render_template_string

# --- Backend (PC) ---
FACE_API_BASE = os.environ.get("FACE_API_BASE", "http://192.168.1.103:8000").rstrip("/")
IDENTIFY_URL = f"{FACE_API_BASE}/api/identify-face"

PHOTO_DIR = os.environ.get("FACE_PHOTO_DIR", "/home/pi/photos")
os.makedirs(PHOTO_DIR, exist_ok=True)

# --- Flux caméra (même esprit que l'ancien rpicam-vid MJPEG) ---
STREAM_WIDTH = int(os.environ.get("STREAM_WIDTH", "640"))
STREAM_HEIGHT = int(os.environ.get("STREAM_HEIGHT", "480"))
STREAM_FPS = int(os.environ.get("STREAM_FPS", "15"))

MJPEG_CMD_CANDIDATES: List[List[str]] = [
    [
        "rpicam-vid",
        "-t",
        "0",
        "--codec",
        "mjpeg",
        "--width",
        str(STREAM_WIDTH),
        "--height",
        str(STREAM_HEIGHT),
        "--framerate",
        str(STREAM_FPS),
        "--inline",
        "-o",
        "-",
    ],
    [
        "libcamera-vid",
        "-t",
        "0",
        "--codec",
        "mjpeg",
        "--width",
        str(STREAM_WIDTH),
        "--height",
        str(STREAM_HEIGHT),
        "--framerate",
        str(STREAM_FPS),
        "--inline",
        "-o",
        "-",
    ],
]

last_jpeg: Optional[bytes] = None
last_jpeg_at: float = 0.0
_stream_proc: Optional[subprocess.Popen] = None
_jpeg_lock = threading.Lock()
_reader_thread: Optional[threading.Thread] = None
_stream_error: Optional[str] = None

app = Flask(__name__)


def _mjpeg_reader_loop():
    """Lit stdout MJPEG, extrait des JPEG complets (FF D8 … FF D9), met à jour last_jpeg."""
    global last_jpeg, last_jpeg_at, _stream_proc, _stream_error

    while True:
        _stream_error = None
        proc: Optional[subprocess.Popen] = None
        for cmd in MJPEG_CMD_CANDIDATES:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0,
                )
                break
            except FileNotFoundError:
                continue
        if proc is None or proc.stdout is None:
            _stream_error = "rpicam-vid / libcamera-vid introuvable"
            time.sleep(3)
            continue

        _stream_proc = proc
        buf = b""
        try:
            while proc.poll() is None:
                chunk = proc.stdout.read(8192)
                if not chunk:
                    break
                buf += chunk
                if len(buf) > 512 * 1024:
                    buf = buf[-256 * 1024 :]

                while True:
                    soi = buf.find(b"\xff\xd8")
                    if soi < 0:
                        break
                    eoi = buf.find(b"\xff\xd9", soi + 2)
                    if eoi < 0:
                        buf = buf[soi : soi + 400 * 1024]
                        break
                    frame = buf[soi : eoi + 2]
                    buf = buf[eoi + 2 :]
                    with _jpeg_lock:
                        last_jpeg = frame
                        last_jpeg_at = time.time()
        except Exception as e:
            _stream_error = str(e)
        finally:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            _stream_proc = None
        time.sleep(1)


def _ensure_reader_started():
    global _reader_thread
    if _reader_thread is not None and _reader_thread.is_alive():
        return
    _reader_thread = threading.Thread(target=_mjpeg_reader_loop, daemon=True)
    _reader_thread.start()


def _capture_jpeg_bytes() -> Tuple[Optional[bytes], Optional[str]]:
    """Repli : photo seule si le flux n'a pas encore d'image (rpicam-still, etc.)."""
    fd, path = tempfile.mkstemp(suffix=".jpg", prefix="face_")
    os.close(fd)
    try:
        candidates = [
            [
                "rpicam-still",
                "-o",
                path,
                "--width",
                "1280",
                "--height",
                "720",
                "-t",
                "500",
                "--nopreview",
            ],
            ["libcamera-still", "-o", path, "--width", "1280", "--height", "720", "-t", "500", "--nopreview"],
            ["raspistill", "-o", path, "-w", "1280", "-h", "720", "-t", "500", "-n"],
        ]
        last_err = None
        for cmd in candidates:
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if r.returncode == 0 and os.path.isfile(path) and os.path.getsize(path) > 0:
                    with open(path, "rb") as f:
                        return f.read(), None
                last_err = r.stderr or r.stdout or f"code {r.returncode}"
            except FileNotFoundError:
                last_err = f"commande absente: {cmd[0]}"
            except subprocess.TimeoutExpired:
                last_err = "timeout capture"
            except Exception as e:
                last_err = str(e)
        return None, last_err or "capture impossible"
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def gen_mjpeg_http():
    """multipart MJPEG pour <img src="/video_feed">."""
    boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
    while True:
        with _jpeg_lock:
            j = last_jpeg
        if j:
            yield boundary + j + b"\r\n"
        time.sleep(max(0.02, 1.0 / max(1, STREAM_FPS)))


PAGE = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Visio + reco visage</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; background:#111; color:#eee; }
    h1 { font-size: 1.25rem; }
    .api { font-size: 0.85rem; color: #888; word-break: break-all; }
    .preview-wrap { background:#000; border-radius:8px; overflow:hidden; margin: 1rem 0; }
    .preview-wrap img { display:block; width:100%; height:auto; min-height:200px; object-fit:contain; }
    button { padding: 0.75rem 1.25rem; font-size: 1rem; cursor: pointer; border-radius: 8px; border: 0; background: #3b82f6; color: #fff; }
    button:disabled { opacity: 0.5; cursor: wait; }
    #out { margin-top: 1rem; padding: 1rem; border-radius: 8px; background: #222; min-height: 3rem; }
    .nom { font-size: 1.5rem; font-weight: 700; color: #4ade80; }
    .inconnu { font-size: 1.5rem; font-weight: 700; color: #f87171; }
    .err { color: #fbbf24; white-space: pre-wrap; font-size: 0.9rem; }
    .hint { font-size: 0.8rem; color: #666; }
  </style>
</head>
<body>
  <h1>Visio caméra → identification</h1>
  <p class="api">API : {{ identify_url }}</p>
  <div class="preview-wrap">
    <img src="/video_feed" alt="Flux caméra"/>
  </div>
  <p class="hint">Image envoyée = dernière frame du flux (pas de 2ᵉ ouverture caméra).</p>
  <p><button id="btn" type="button">Identifier (photo actuelle)</button></p>
  <div id="out">Choisis un cadre dans le flux puis clique.</div>
  <script>
    const btn = document.getElementById('btn');
    const out = document.getElementById('out');
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      out.textContent = 'Envoi au backend…';
      try {
        const r = await fetch('/snap', { method: 'POST' });
        const j = await r.json();
        if (!r.ok) {
          out.innerHTML = '<span class="err">' + (j.detail || j.error || JSON.stringify(j)) + '</span>';
          return;
        }
        const nom = (j.nom || 'inconnu').toString();
        if (nom.toLowerCase() === 'inconnu') {
          out.innerHTML = '<span class="inconnu">inconnu</span>';
        } else {
          out.innerHTML = '<span class="nom">' + nom.replace(/</g,'&lt;') + '</span>';
        }
      } catch (e) {
        out.innerHTML = '<span class="err">' + e + '</span>';
      } finally {
        btn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.get("/")
def index():
    _ensure_reader_started()
    return render_template_string(PAGE, identify_url=IDENTIFY_URL)


@app.get("/video_feed")
def video_feed():
    _ensure_reader_started()
    return Response(
        gen_mjpeg_http(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.post("/snap")
def snap():
    _ensure_reader_started()
    max_age = float(os.environ.get("SNAP_MAX_FRAME_AGE", "3.0"))

    with _jpeg_lock:
        j = last_jpeg
        t = last_jpeg_at

    if j and (time.time() - t) <= max_age:
        data = j
    else:
        data, cap_err = _capture_jpeg_bytes()
        if not data:
            msg = cap_err or "aucune image du flux (attends 1–2 s) ni capture still"
            if _stream_error:
                msg += f" | flux: {_stream_error}"
            return jsonify({"error": msg}), 500

    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(os.path.join(PHOTO_DIR, f"capture_{stamp}.jpg"), "wb") as f:
            f.write(data)
    except OSError:
        pass

    try:
        r = requests.post(
            IDENTIFY_URL,
            files={"file": ("capture.jpg", data, "image/jpeg")},
            timeout=60,
        )
    except requests.RequestException as e:
        return jsonify({"error": f"réseau / backend: {e}"}), 503

    try:
        body = r.json()
    except Exception:
        return jsonify({"error": r.text[:500] or f"HTTP {r.status_code}"}), 502

    if r.status_code != 200:
        detail = body.get("detail") if isinstance(body, dict) else str(body)
        return jsonify({"detail": detail, "raw": body}), r.status_code

    return jsonify(body)


if __name__ == "__main__":
    _ensure_reader_started()
    print("Backend reco :", IDENTIFY_URL)
    print("Flux MJPEG : http://0.0.0.0:5000/video_feed")
    print("Page : http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False, threaded=True)
