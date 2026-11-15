"""`sar audio`: the before and after ambience for each place (Layer 5, muted until the reader turns it on).

Recordings come from Wikimedia Commons (public domain or CC0 only), downloaded once, cut to a 30 s loop with
short fades, and encoded as mono MP3 at 64 kbit/s (about 240 kB, which every browser plays). None was recorded
at the place itself, and the label says so. Where Commons has nothing suitable the loop is synthesized with
numpy and labeled as synthesized.
"""

from __future__ import annotations

import subprocess
import urllib.parse
import urllib.request
import wave
from pathlib import Path

import numpy as np

from .config import CACHE_DIR, CHAPTERS_DIR, DATA_DIR, load_config
from .manifest import read_manifest, write_manifest

LOOP_S = 30.0
FADE_S = 1.5
RATE = 44_100
MAX_BYTES = 800_000
USER_AGENT = "dancing-with-sars-pipeline/0.1 (NASA Space Apps 2026 project)"
SYNTH_URL = "https://github.com/benhoangquan/dancing-with-sars/blob/main/pipeline/src/sarstory/audio.py"


def get(url: str, tries: int = 5) -> bytes:
    """GET with backoff: Wikimedia answers 429 when requests come too fast."""
    import time
    import urllib.error

    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 (fixed https hosts)
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == tries - 1:
                raise
            time.sleep(5 * 2**attempt)
    raise AssertionError("unreachable")


def ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def commons_file(title: str) -> dict:
    """URL, licence and author of a Commons file. Only public domain and CC0 are accepted."""
    q = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
        }
    )
    req = urllib.request.Request(
        f"https://commons.wikimedia.org/w/api.php?{q}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (fixed https host)
        import json

        page = next(iter(json.load(r)["query"]["pages"].values()))
    info = page["imageinfo"][0]
    meta = info["extmetadata"]
    licence = meta.get("LicenseShortName", {}).get("value", "")
    if licence not in {"Public domain", "CC0"}:
        raise RuntimeError(f"{title}: licence {licence!r} is not public domain or CC0")
    import re

    artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "unknown")).strip()
    return {
        "url": info["url"].split("?")[0],
        "page": info["descriptionurl"],
        "license": licence,
        "artist": artist,
    }


def synth(kind: str, seconds: float = LOOP_S, seed: int = 7) -> np.ndarray:
    """A seamless loop of wind (brown noise, slow gusts), with fire crackle for `kind` == "fire"."""
    rng = np.random.default_rng(seed)
    n = int(seconds * RATE)
    brown = np.cumsum(rng.normal(0, 1, n))
    brown -= np.convolve(brown, np.ones(4001) / 4001, mode="same")  # drop the drift, keep the rumble
    brown /= np.abs(brown).max() + 1e-9
    t = np.arange(n) / RATE
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * t / seconds * 3) ** 2  # whole cycles so the loop is seamless
    out = 0.35 * brown * gust
    if kind == "fire":
        for start in rng.integers(0, n - 2000, size=int(seconds * 9)):
            length = int(rng.integers(200, 1600))
            pop = rng.normal(0, 1, length) * np.exp(-np.arange(length) / (length / 5))
            out[start : start + length] += 0.5 * rng.uniform(0.2, 1.0) * pop
    return np.clip(out / (np.abs(out).max() + 1e-9) * 0.8, -1, 1).astype(np.float32)


def write_wav(path: Path, samples: np.ndarray) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((samples * 32767).astype("<i2").tobytes())


def encode_loop(src: Path, dst: Path, start_s: float = 0.0) -> None:
    fade_out = LOOP_S - FADE_S
    cmd = [
        ffmpeg(),
        "-y",
        "-loglevel",
        "error",
        "-ss",
        str(start_s),
        "-t",
        str(LOOP_S),
        "-i",
        str(src),
        "-ac",
        "1",
    ]
    cmd += [
        "-af",
        f"afade=t=in:d={FADE_S},afade=t=out:st={fade_out}:d={FADE_S}",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "64k",
    ]
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([*cmd, str(dst)], check=True, timeout=300)
    if dst.stat().st_size > MAX_BYTES:
        raise RuntimeError(f"{dst.name} is {dst.stat().st_size / 1e3:.0f} kB, over {MAX_BYTES / 1e3:.0f} kB")


def build_audio(
    slug: str, *, data_dir: Path = DATA_DIR, chapters_dir: Path = CHAPTERS_DIR, log=print
) -> Path:
    spec = load_config(slug)["soundscape"]
    manifest = read_manifest(slug, chapters_dir)
    cache = CACHE_DIR / "audio"
    cache.mkdir(parents=True, exist_ok=True)
    out = {}
    for side in ("before", "after"):
        s = spec[side]
        dst = data_dir / slug / f"sound_{side}.mp3"
        if "commons" in s:
            info = commons_file(s["commons"])
            raw = cache / Path(urllib.parse.unquote(info["url"])).name
            if not raw.exists():
                raw.write_bytes(get(info["url"]))
            encode_loop(raw, dst, s.get("start_s", 0.0))
            entry = {
                "label": s["label"],
                "credit": f"{info['artist']}, via Wikimedia Commons. Not recorded at this place.",
                "license": info["license"],
                "sourceUrl": info["page"],
                "synthesized": False,
            }
        else:
            wav = cache / f"synth_{s['synth']}.wav"
            write_wav(wav, synth(s["synth"]))
            encode_loop(wav, dst)
            entry = {
                "label": s["label"],
                "credit": "Synthesized for this site with numpy (wind noise and crackle). Not a recording.",
                "license": "CC0",
                "sourceUrl": SYNTH_URL,
                "synthesized": True,
            }
        out[side] = {"src": dst.relative_to(data_dir.parent).as_posix(), **entry}
        log(f"  {side}: {dst.stat().st_size / 1e3:.0f} kB, {entry['credit']}")
    manifest["soundscape"] = out
    return write_manifest(slug, manifest, chapters_dir)
