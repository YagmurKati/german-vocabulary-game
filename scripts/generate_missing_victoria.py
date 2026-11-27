#!/usr/bin/env python3
"""Generate missing German WortFlip MP3s with the free Victoria TTS server.

The 1,600 existing German recordings are never overwritten. All new clips,
including the eight preview clips, are saved at the voice's NORMAL 100% speed.
Playback speed is a user preference, never baked into the new individual MP3s.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

from generate_listening_mp3 import ROOT, GROUP_SOURCES, load_cards

BASE_URL='http://127.0.0.1:7860'
VOICE='df_victoria'
AUDIO_DIR=ROOT/'audio'
MANIFEST=AUDIO_DIR/'tracks.json'
MISSING={
    'lookalikes':(400,'l','y'),
    'nouns':(0,'n','z'),
    'speaking':(0,'s','t'),
    'verbs':(0,'v','w'),
}
SIZES={'lookalikes':500,'everyday':400,'nouns':200,'speaking':100,'verbs':100}
KEYS={'lookalikes':('lookalikes','lookalike_examples'),
      'nouns':('nouns','noun_examples'), 'speaking':('speaking','speaking_examples'),
      'verbs':('verbs','verb_examples')}


def expected_clips(source):
    clips=[]
    for group,(start,w,e) in MISSING.items():
        for idx in range(start,len(source[group])):
            card=source[group][idx]
            for field,prefix in (('de',w),('example',e)):
                phrase=card[field].strip()
                if not phrase: raise ValueError(f'Empty {field}: {group} #{idx}')
                clips.append((group,idx,field,phrase,AUDIO_DIR/f'{prefix}{idx:03d}.mp3'))
    if len(clips)!=1000: raise ValueError(f'Expected 1000 missing clips, got {len(clips)}')
    return clips


def synthesize(phrase):
    data=json.dumps({'model':'kokoro','voice':VOICE,'input':phrase,
                     'response_format':'mp3','speed':1.0}).encode('utf-8')
    req=urllib.request.Request(BASE_URL+'/v1/audio/speech',data=data,
        headers={'Content-Type':'application/json','Accept':'audio/mpeg'},method='POST')
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=300) as response:
                content=response.read()
                if 'audio/' not in response.headers.get('Content-Type',''):
                    raise RuntimeError(f'Unexpected format: {response.headers.get("Content-Type")}')
                if len(content)<500 or not content.startswith((b'ID3',b'\xff\xfb',b'\xff\xf3',b'\xff\xf2')):
                    raise ValueError('Server did not return MP3 data')
                return content
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,RuntimeError) as err:
            if attempt==3: raise RuntimeError(f'Victoria TTS failed for {phrase[:55]!r}') from err
            print(f'TTS retry {attempt+1}/3: {str(err)[:160]}',flush=True)
            time.sleep(8*(attempt+1))
    raise AssertionError('unreachable')


def extend_manifest(source):
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('version')!=1: raise ValueError('Unexpected audio manifest version')
    collection=manifest['collections']
    for group,(start,w,e) in MISSING.items():
        word_key,example_key=KEYS[group]
        original_words=collection.get(word_key,[])
        original_examples=collection.get(example_key,[])
        words=[{'text':x['de'],'file':f'audio/{w}{i:03d}.mp3'} for i,x in enumerate(source[group])]
        examples=[{'text':x['example'],'file':f'audio/{e}{i:03d}.mp3'} for i,x in enumerate(source[group])]
        if start and (original_words[:start]!=words[:start] or original_examples[:start]!=examples[:start]):
            raise ValueError(f'{group}: existing track manifest differs from vocabulary; no files changed')
        collection[word_key]=words
        collection[example_key]=examples
    manifest['additional_voice']={'id':VOICE,'source':'Free German Victoria Kokoro voice',
        'scope':'500 additional cards and their German example sentences',
        'existing_clips_preserved':True,'recorded_speed':1.0,
        'playback_speed_options':[1.0,0.8,0.6,0.4]}
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode',choices=('preview','all'),default='preview')
    mode=ap.parse_args().mode
    text=(ROOT/'index.html').read_text(encoding='utf-8')
    source={g:load_cards(text,n) for g,n in GROUP_SOURCES.items()}
    for group,size in SIZES.items():
        if len(source[group])!=size:raise ValueError(f'Expected {size} {group} cards')
    clips=expected_clips(source)
    if mode=='preview':
        clips=[x for x in clips if x[1]==MISSING[x[0]][0]]
        if len(clips)!=8:raise ValueError('Expected eight preview clips')
        (ROOT/'victoria-preview').mkdir(exist_ok=True)
    made=skipped=0
    for n,(group,idx,field,phrase,destination) in enumerate(clips,1):
        if mode=='preview':
            destination=ROOT/'victoria-preview'/f'{group}-{destination.name}'
        # Do not rewrite already present recordings. Existing MP3s always survive.
        if destination.exists() and destination.stat().st_size>500:
            skipped+=1;continue
        voice_data=synthesize(phrase)
        destination.parent.mkdir(exist_ok=True,parents=True)
        tmp=destination.with_suffix('.mp3.tmp')
        tmp.write_bytes(voice_data)
        tmp.replace(destination)
        made+=1
        if mode=='preview' or n%25==0 or n==len(clips):
            print(f'[{n}/{len(clips)}] {group} #{idx} {field}: made={made}, kept={skipped}',flush=True)
    if mode=='all':
        missing=[str(x[-1]) for x in expected_clips(source) if not x[-1].exists()]
        if missing: raise ValueError(f'Missing {len(missing)} new clips, e.g. {missing[:3]}')
        extend_manifest(source)
    print(f'{mode} complete at ORIGINAL speaking speed: {made} made; {skipped} kept.')

if __name__=='__main__':main()
