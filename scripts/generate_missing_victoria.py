#!/usr/bin/env python3
"""Generate *only* WortFlip's 1,000 previously missing German clips.

Uses a free KokoroTTS server running on the SAME GitHub Actions runner,
with the dedicated, Apache-2.0 German female model `df_victoria`.
Already-published 1,600 German recordings are never overwritten.

`--mode preview` generates 8 trial clips without altering the app.
`--mode all` creates only missing audio files and extends the manifest.
New audio is stored at natural speed. The browser and 30-minute builder
play EVERY German recording at half-speed with pitch preservation.
Preview MP3s are stretched to the requested 0.5x for representative listening.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

from generate_listening_mp3 import ROOT, GROUP_SOURCES, load_cards

BASE_URL = 'http://127.0.0.1:7860'
VOICE = 'df_victoria'  # Exact German Victoria voice, NOT a standard English Kokoro voice.
AUDIO_DIR = ROOT / 'audio'
MANIFEST = AUDIO_DIR / 'tracks.json'
MISSING = {
    'lookalikes': (400, 'l', 'y'),  # indices 400-499
    'nouns': (0, 'n', 'z'),          # indices 0-199
    'speaking': (0, 's', 't'),       # indices 0-99
    'verbs': (0, 'v', 'w'),          # indices 0-99
}
SIZES = {'lookalikes': 500, 'everyday': 400, 'nouns': 200, 'speaking': 100, 'verbs': 100}
MANIFEST_KEYS = {
    'lookalikes': ('lookalikes', 'lookalike_examples'),
    'nouns': ('nouns', 'noun_examples'),
    'speaking': ('speaking', 'speaking_examples'),
    'verbs': ('verbs', 'verb_examples'),
}


def expected_clips(source):
    clips = []
    for group, (start, word_prefix, example_prefix) in MISSING.items():
        for idx in range(start, len(source[group])):
            card = source[group][idx]
            for field, prefix in [('de', word_prefix), ('example', example_prefix)]:
                text = card[field].strip()
                if not text:
                    raise ValueError(f'Empty German text for {group} #{idx} {field}')
                clips.append((group, idx, field, text, AUDIO_DIR / f'{prefix}{idx:03d}.mp3'))
    if len(clips) != 1000:
        raise ValueError(f'Expected exactly 1000 missing German clips, not {len(clips)}')
    return clips


def api_request(phrase):
    payload = json.dumps({
        'model': 'kokoro',
        'voice': VOICE,
        'input': phrase,
        'response_format': 'mp3',
        'speed': 1.0,  # Deliberately normal: slowing happens only on PLAYBACK.
    }).encode('utf-8')
    request = urllib.request.Request(
        BASE_URL + '/v1/audio/speech',
        data=payload,
        headers={'Content-Type': 'application/json', 'Accept': 'audio/mpeg'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        data = response.read()
        if 'audio/' not in response.headers.get('Content-Type', ''):
            raise RuntimeError(f'Unexpected TTS response: {response.headers.get("Content-Type")}')
        return data


def synthesize(phrase):
    for attempt in range(4):
        try:
            data = api_request(phrase)
            if len(data) < 500 or not data.startswith((b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2')):
                raise ValueError('Speech API did not return valid MP3 data')
            return data
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as exc:
            if attempt == 3:
                raise RuntimeError(f'Victoria TTS failed for {phrase[:60]!r}') from exc
            print(f'TTS retry {attempt+1}/3: {str(exc)[:220]}', flush=True)
            time.sleep(8 * (attempt + 1))
    raise AssertionError('unreachable')


def update_manifest(source):
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('version') != 1:
        raise ValueError('Unexpected original audio manifest version')
    collections = manifest['collections']
    for key in ('lookalikes', 'everyday', 'examples', 'lookalike_examples'):
        n = len(collections[key])
        if n not in ((400, 500) if key in ('lookalikes', 'lookalike_examples') else (400,)):
            raise ValueError(f'Existing audio collection {key} has unexpected length {n}')

    for group, (start, word_prefix, example_prefix) in MISSING.items():
        words_key, examples_key = MANIFEST_KEYS[group]
        words = [{'text':c['de'], 'file':f'audio/{word_prefix}{i:03d}.mp3'} for i, c in enumerate(source[group])]
        examples = [{'text':c['example'], 'file':f'audio/{example_prefix}{i:03d}.mp3'} for i, c in enumerate(source[group])]
        if start:
            if collections[words_key][:start] != words[:start] or collections[examples_key][:start] != examples[:start]:
                raise ValueError(f'Existing {group} clips do not match manifest; refusing to overwrite')
        collections[words_key] = words
        collections[examples_key] = examples

    manifest['additional_voice'] = {
        'id': VOICE,
        'source': 'kikiri-tts/kikiri-german-victoria (Apache-2.0)',
        'scope': '500 new German word/phrase recordings and their 500 example sentences',
        'existing_clips_preserved': True,
        'player_speech_rate': 0.5,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['preview', 'all'], default='preview')
    opts = ap.parse_args()
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    source = {g:load_cards(html, cname) for g, cname in GROUP_SOURCES.items()}
    for g, size in SIZES.items():
        if len(source[g]) != size:
            raise ValueError(f'Expected {size} {g} cards, found {len(source[g])}')
    clips = expected_clips(source)
    if opts.mode == 'preview':
        clips = [row for row in clips if row[1] == MISSING[row[0]][0]]
        assert len(clips) == 8
    preview_dir = ROOT / 'victoria-preview'
    if opts.mode == 'preview':
        preview_dir.mkdir(exist_ok=True)
    made, skipped = 0, 0
    for n, (group, idx, field, phrase, output) in enumerate(clips, 1):
        if opts.mode == 'preview':
            output = preview_dir / (group + '-' + output.name)
        if output.is_file() and output.stat().st_size > 500:
            skipped += 1
            continue
        data = synthesize(phrase)
        if opts.mode == 'preview':
            data = subprocess.run([
                'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                '-i', 'pipe:0', '-af', 'atempo=0.5', '-codec:a', 'libmp3lame',
                '-b:a', '48k', '-f', 'mp3', 'pipe:1',
            ], input=data, capture_output=True, check=True).stdout
        output.parent.mkdir(exist_ok=True, parents=True)
        temp = output.with_suffix(output.suffix + '.tmp')
        temp.write_bytes(data)
        temp.replace(output)
        made += 1
        if opts.mode == 'preview' or n % 25 == 0 or n == len(clips):
            print(f'[{n}/{len(clips)}] {group} #{idx} {field}: {made} made, {skipped} kept', flush=True)
    if opts.mode == 'all':
        missing = [str(p) for *_, p in expected_clips(source) if not p.is_file()]
        if missing:
            raise ValueError(f'{len(missing)} new clips still missing: {missing[:5]}')
        update_manifest(source)
    print(f'Completed {opts.mode}: {made} generated, {skipped} previously present; 1600 existing clips unchanged.', flush=True)


if __name__ == '__main__':
    main()
