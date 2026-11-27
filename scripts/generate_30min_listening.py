#!/usr/bin/env python3
"""Create continuous 30+ minute MP3 sessions from existing WortFlip cards.

Uses the repository's existing Piper WAV synthesis and exact English/German
sequence. One file plays without JavaScript scheduling between cards.
Run in repository root (GitHub Actions workflow included).
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from generate_listening_mp3 import ROOT, GROUP_SOURCES, SAMPLE_RATE, load_cards, get_pcm, silence

MIN_SECONDS = 30 * 60  # Minimum length, including the final complete card
OUTPUT_DIR = ROOT / "listening" / "audio30"
MANIFEST = ROOT / "listening" / "30min-sessions.json"
GROUP_LABELS = {
    "lookalikes": "English lookalikes",
    "everyday": "Everyday expressions",
    "nouns": "Practical nouns",
    "speaking": "Conversational nouns",
    "verbs": "Everyday verbs",
}


def append_card(pipe, card, voice_en, voice_de) -> float:
    """Append four spoken parts and recall gaps to a single MP3 encoder."""
    length = 0.0
    for key, voice, pause in (
        ("en", voice_en, 2.5),
        ("de", voice_de, 0.7),
        ("exampleEn", voice_en, 2.5),
        ("example", voice_de, 1.15),
    ):
        phrase = card.get(key, "").strip()
        if not phrase:
            raise ValueError(f"Card field {key} missing: {card!r}")
        pcm = get_pcm(voice, phrase)
        pipe.write(pcm)
        silence_pcm = silence(pause)
        pipe.write(silence_pcm)
        length += (len(pcm) + len(silence_pcm)) / (SAMPLE_RATE * 2)
    return length


def render_session(group: str, cards: list, start: int, sequence: int, voices: dict):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{group}-{sequence:02d}.mp3"
    dest = OUTPUT_DIR / file_name
    # Always render from the current card content when the workflow is run.
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", "1", "-i", "pipe:0",
        "-vn", "-codec:a", "libmp3lame", "-b:a", "48k", str(dest),
    ]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    length = 0.0
    original_index = start
    played = 0
    replayed = 0
    try:
        assert proc.stdin is not None
        proc.stdin.write(silence(0.5))
        length += 0.5
        while length < MIN_SECONDS:
            # Fill the last session by revisiting the beginning of that collection.
            # Do NOT skip its final cards and do NOT start the next category.
            index = original_index if original_index < len(cards) else (replayed % len(cards))
            if original_index < len(cards):
                original_index += 1
            else:
                replayed += 1
            length += append_card(proc.stdin, cards[index], voices["en"], voices["de"])
            played += 1
            if played % 25 == 0:
                print(f"  {group} session {sequence}: {length / 60:.1f} minutes ({played} cards)", flush=True)
        proc.stdin.close()
        code = proc.wait()
        if code:
            raise RuntimeError(f"ffmpeg exited {code} while writing {dest}")
    except BaseException:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        proc.kill()
        proc.wait()
        dest.unlink(missing_ok=True)
        raise
    if not dest.is_file() or dest.stat().st_size < 200_000:
        raise RuntimeError(f"Output MP3 is missing or unexpectedly small: {dest}")
    result = {
        "id": f"{group}-{sequence:02d}",
        "group": group,
        "label": f"{GROUP_LABELS[group]} · session {sequence}",
        "file": f"listening/audio30/{file_name}",
        "seconds": round(length),
        "minutes": round(length / 60, 1),
        "cards": played,
        "first_card": start + 1,
        "last_new_card": original_index,
        "repeated_cards": replayed,
    }
    return result, original_index


def main():
    from piper import PiperVoice

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    source = {group: load_cards(html, name) for group, name in GROUP_SOURCES.items()}
    if sum(map(len, source.values())) != 1300:
        raise ValueError("Expected the published set of 1,300 WortFlip cards")
    voices = {
        "en": PiperVoice.load(str((ROOT / "en_US-lessac-medium.onnx").resolve())),
        "de": PiperVoice.load(str((ROOT / "de_DE-thorsten-medium.onnx").resolve())),
    }
    sessions = []
    for group, cards in source.items():
        index = 0
        number = 0
        while index < len(cards):
            number += 1
            print(f"Rendering {GROUP_LABELS[group]} #{number}, starting card {index + 1}", flush=True)
            result, next_index = render_session(group, cards, index, number, voices)
            sessions.append(result)
            index = next_index
            print(f"Created {result['minutes']} minutes: {result['file']}", flush=True)
    MANIFEST.write_text(json.dumps({
        "version": 1,
        "description": "Continuous 30+ minute English–German lessons made from the existing 1,300 WortFlip cards",
        "sequence": "English prompt, 2.5s pause, German answer, English example, 2.5s pause, German example",
        "sessions": sessions,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {len(sessions)} 30+ minute sessions; saved {MANIFEST}", flush=True)


if __name__ == "__main__":
    main()
