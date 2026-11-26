#!/usr/bin/env python3
"""Build screen-lock-friendly bilingual MP3 lessons from WortFlip's existing cards.

Uses Piper for US English and German; emits a fixed 2.5-second recall pause
before each German word and each German sentence. All text is from index.html.
No content is invented or changed by this script.
"""
from __future__ import annotations

import argparse
import audioop  # Python 3.11, intentionally used by the GitHub Actions workflow
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import wave

ROOT = Path(__file__).resolve().parents[1]
GROUP_SOURCES = {
    "lookalikes": "LOOKALIKE_CARDS",
    "everyday": "EVERYDAY_CARDS",
    "nouns": "NOUN_CARDS",
    "speaking": "SPEAKING_CARDS",
    "verbs": "VERB_CARDS",
}
SAMPLE_RATE = 24000


def load_cards(html: str, const_name: str) -> list[dict]:
    match = re.search(r"\bconst\s+" + re.escape(const_name) + r"\s*=\s*", html)
    if not match:
        raise ValueError(f"Missing {const_name} in index.html")
    obj, _ = json.JSONDecoder().raw_decode(html[match.end():])
    if not isinstance(obj, list):
        raise ValueError(f"Invalid {const_name}: expected a JSON array")
    return obj


def get_pcm(voice, line: str) -> bytes:
    # Each phrase is synthesized only once, without speech overlapping the pauses.
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        voice.synthesize_wav(line, wav)
    buffer.seek(0)
    with wave.open(buffer, "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("Piper output was not mono 16-bit PCM")
        samples = wav.readframes(wav.getnframes())
        input_rate = wav.getframerate()
    if input_rate != SAMPLE_RATE:
        samples, _ = audioop.ratecv(samples, 2, 1, input_rate, SAMPLE_RATE, None)
    return samples


def silence(seconds: float) -> bytes:
    return bytes(round(seconds * SAMPLE_RATE) * 2)


def write_lesson(lesson, data, voices, output: Path) -> None:
    src = data[lesson["group"]]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wavpath = Path(tmp) / "lesson.wav"
        with wave.open(str(wavpath), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(silence(.5))
            for i in lesson["indices"]:
                c = src[i]
                for key, lang, gap in (
                    ("en", "en", 2.5),
                    ("de", "de", .7),
                    ("exampleEn", "en", 2.5),
                    ("example", "de", 1.15),
                ):
                    phrase = c[key].strip()
                    if not phrase:
                        raise ValueError(f"Empty {key}: {lesson['id']} card {i}")
                    wav.writeframes(get_pcm(voices[lang], phrase))
                    wav.writeframes(silence(gap))
        subprocess.run([
            "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(wavpath), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
            "-codec:a", "libmp3lame", "-b:a", "40k", str(output),
        ], check=True)
    if output.stat().st_size < 20000:
        raise RuntimeError(f"Unexpectedly short MP3: {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preview", "all"), default="preview")
    parser.add_argument("--en-model", default="en_US-lessac-medium.onnx")
    parser.add_argument("--de-model", default="de_DE-thorsten-medium.onnx")
    args = parser.parse_args()

    from piper import PiperVoice

    index = (ROOT / "index.html").read_text(encoding="utf-8")
    data = {g: load_cards(index, n) for g, n in GROUP_SOURCES.items()}
    catalog = json.loads((ROOT / "listening/lessons.json").read_text(encoding="utf-8"))
    lessons = catalog["lessons"]
    if len(lessons) != 65 or sum(len(l["indices"]) for l in lessons) != 1300:
        raise ValueError("Unexpected lesson catalog: must cover exactly 1300 existing cards")
    if sum(len(x) for x in data.values()) != 1300:
        raise ValueError("Card count in index.html has changed; recreate lesson catalog")

    voices = {
        "en": PiperVoice.load(str(Path(args.en_model).resolve())),
        "de": PiperVoice.load(str(Path(args.de_model).resolve())),
    }
    selection = lessons[:2] if args.mode == "preview" else lessons
    for n, lesson in enumerate(selection, 1):
        output = ROOT / lesson["file"]
        if output.is_file() and output.stat().st_size >= 20000:
            print(f"[{n}/{len(selection)}] Already recorded: {lesson['id']}", flush=True)
            continue
        print(f"[{n}/{len(selection)}] Recording {lesson['id']}: {lesson['group']} / {lesson['label']}", flush=True)
        write_lesson(lesson, data, voices, output)
        print(f"  {output.stat().st_size // 1024} KiB written", flush=True)
    print("Audio generation complete.", flush=True)

if __name__ == "__main__":
    main()
