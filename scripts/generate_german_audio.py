#!/usr/bin/env python3
"""Create identical German MP3 clips on GitHub from Wortspiel's audio track list.
This script uses one de-DE Piper model for ALL clips, no device TTS.
Requires: pip install piper-tts, ffmpeg, de_DE-thorsten-medium downloaded.
"""
from __future__ import annotations
import argparse, json, subprocess, wave, tempfile
from pathlib import Path
from piper import PiperVoice

BASE=Path(__file__).resolve().parents[1]
LIST=BASE/'audio'/'tracks.json'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',default='de_DE-thorsten-medium.onnx')
    parser.add_argument('--limit',type=int,default=0,help='For trial runs; 0 generates all tracks')
    parser.add_argument('--preview',action='store_true',help='Generate an audio-quality sample set only')
    args=parser.parse_args()
    data=json.loads(LIST.read_text(encoding='utf-8'))
    names=('lookalikes','everyday','examples')
    entries=[x for key in names for x in data['collections'][key]]
    assert len(entries)==1200, len(entries)
    if args.preview:
        chosen={'sich engagieren','arrangieren','das Restaurant','fotografieren','sich konzentrieren','in den Bus einsteigen','aus dem Bus aussteigen','einen Termin absagen','die Treppe','der Ausgang'}
        entries=[x for x in entries if x['text'] in chosen][:10]
        assert len(entries)==len(chosen), (len(entries),len(chosen))
    if args.limit:entries=entries[:args.limit]
    model=Path(args.model).resolve()
    if not model.is_file():raise SystemExit(f'Voice model missing: {model}')
    voice=PiperVoice.load(str(model))
    generated=0
    with tempfile.TemporaryDirectory() as tmp:
        tmpwav=Path(tmp)/'input.wav'
        for i,item in enumerate(entries,1):
            dest=BASE/item['file']
            dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists() and dest.stat().st_size>1024:
                continue
            with wave.open(str(tmpwav),'wb') as stream:
                voice.synthesize_wav(item['text'],stream)
            # Mono, fixed encoding, consistent across devices
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                '-i',str(tmpwav),'-vn','-ac','1','-ar','24000',
                '-codec:a','libmp3lame','-b:a','48k',str(dest)],check=True)
            if dest.stat().st_size<800:raise RuntimeError(f'Suspiciously short audio: {dest}')
            generated+=1
            if i%50==0:print(f'Processed {i}/{len(entries)} clips ({generated} new)',flush=True)
    print(f'Done: {len(entries)} clips verified, {generated} generated')

if __name__=='__main__':main()
