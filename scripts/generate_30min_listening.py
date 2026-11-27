#!/usr/bin/env python3
"""Rebuild 30+ minute WortFlip sessions from existing German recordings.

English is generated at its original speaking speed with the original Piper
English voice. German: the already recorded Thorsten clips are slowed to 0.5x
without lowering pitch, and new Victoria German clips are slowed to 0.5x as well. 1,600 existing German MP3s are read, never overwritten or regenerated.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess

from generate_listening_mp3 import ROOT, GROUP_SOURCES, SAMPLE_RATE, load_cards, get_pcm, silence

MIN_SECONDS=1800
OUTPUT_DIR=ROOT/'listening'/'audio30'
MANIFEST=ROOT/'listening'/'30min-sessions.json'
LABELS={'lookalikes':'English lookalikes','everyday':'Everyday expressions','nouns':'Practical nouns','speaking':'Conversational nouns','verbs':'Everyday verbs'}
# First 800 cards use the *existing* recordings by the original German male.
# Remaining 500 cards use the newly generated Victoria recordings.
CLIPS={
 'lookalikes':('l','y'),
 'everyday':('e','x'),
 'nouns':('n','z'),
 'speaking':('s','t'),
 'verbs':('v','w'),
}

def original_male(group,index):
    return group=='everyday' or (group=='lookalikes' and index<400)


def pcm_for_german(group,index,example,cache):
    prefix=CLIPS[group][1 if example else 0]
    path=ROOT/'audio'/f'{prefix}{index:03d}.mp3'
    key=path
    if key not in cache:
        if not path.is_file() or path.stat().st_size<500:
            raise FileNotFoundError(f'{path} is missing. Run the Seraphina workflow in all mode first.')
        command=['ffmpeg','-nostdin','-v','error','-i',str(path)]
        # Half-speed time stretching with preserved pitch, unlike naive
        # 0.5x sample-rate playback. Works on already stored MP3s.
        # All German clips play at 0.5x with pitch preserved.
        command += ['-af','atempo=0.5']
        command += ['-f','s16le','-acodec','pcm_s16le','-ar',str(SAMPLE_RATE),'-ac','1','pipe:1']
        data=subprocess.check_output(command)
        if len(data)<500:
            raise ValueError(f'Cannot decode {path}')
        cache[key]=data
    return cache[key]


def write_card(pipe, group, index, card, english_voice, cache):
    length=0
    parts=[
        (get_pcm(english_voice, card['en'].strip()), 2.5),
        (pcm_for_german(group,index,False,cache), .7),
        (get_pcm(english_voice, card['exampleEn'].strip()), 2.5),
        (pcm_for_german(group,index,True,cache), 1.15),
    ]
    for spoken,gap in parts:
        pipe.write(spoken)
        pause=silence(gap)
        pipe.write(pause)
        length+=(len(spoken)+len(pause))/(SAMPLE_RATE*2)
    return length


def render(group,cards,start,n,english_voice,cache):
    OUTPUT_DIR.mkdir(exist_ok=True,parents=True)
    dest=OUTPUT_DIR/f'{group}-{n:02d}.mp3'
    p=subprocess.Popen(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
                        '-f','s16le','-ar',str(SAMPLE_RATE),'-ac','1','-i','pipe:0',
                        '-vn','-codec:a','libmp3lame','-b:a','48k',str(dest)],stdin=subprocess.PIPE)
    duration=.5
    next_index=start
    played=0
    repeated=0
    try:
        assert p.stdin is not None
        p.stdin.write(silence(.5))
        while duration<MIN_SECONDS:
            # Repeat some cards at the end of the last session to reach >=30 min.
            idx=next_index if next_index<len(cards) else repeated%len(cards)
            if next_index<len(cards):next_index+=1
            else:repeated+=1
            duration+=write_card(p.stdin,group,idx,cards[idx],english_voice,cache)
            played+=1
            if played%25==0:print(f'  {group} #{n}: {duration/60:.1f} min ({played} cards)',flush=True)
        p.stdin.close()
        code=p.wait()
        if code:raise RuntimeError(f'ffmpeg exited {code} writing {dest}')
    except BaseException:
        if p.stdin and not p.stdin.closed:p.stdin.close()
        p.kill();p.wait();dest.unlink(missing_ok=True)
        raise
    if not dest.is_file() or dest.stat().st_size < 200_000:
        raise RuntimeError(f'Bad output file: {dest}')
    return dict(id=f'{group}-{n:02d}',group=group,
                label=f'{LABELS[group]} · session {n}',file=f'listening/audio30/{dest.name}',
                seconds=round(duration),minutes=round(duration/60,1),cards=played,
                first_card=start+1,last_new_card=next_index,repeated_cards=repeated),next_index


def main():
    from piper import PiperVoice
    html=(ROOT/'index.html').read_text(encoding='utf-8')
    source={g:load_cards(html,name) for g,name in GROUP_SOURCES.items()}
    if sum(map(len,source.values()))!=1300:
        raise ValueError('Expected exactly 1300 cards; repository data has changed')
    manifest=json.loads((ROOT/'audio'/'tracks.json').read_text(encoding='utf-8'))
    if len(manifest['collections'].get('lookalikes',[]))!=500:
        raise ValueError('Generate 1000 missing Victoria clips before rebuilding the full 30-minute sessions')
    voice=PiperVoice.load(str((ROOT/'en_US-lessac-medium.onnx').resolve()))
    # Also publish the precise source card text used by the optional device-voice player.
    # This never modifies vocabulary or learning progress.
    device_cards={group:[{field:card[field] for field in ('en','de','exampleEn','example')}
                         for card in cards] for group,cards in source.items()}
    (ROOT/'listening'/'30min-device-cards.json').write_text(
        json.dumps({'version':1,'cards':device_cards},ensure_ascii=False,separators=(',',':'))+'\n',
        encoding='utf-8')
    sessions=[]
    for group,cards in source.items():
        cache={}
        pos=0;number=0
        while pos<len(cards):
            number+=1
            print(f'Building {group} #{number} from card {pos+1}',flush=True)
            session,next_pos=render(group,cards,pos,number,voice,cache)
            sessions.append(session)
            pos=next_pos
        cache.clear()
    MANIFEST.write_text(json.dumps({
        'version':2,
        'description':'Bilingual 30+ minute sessions: original-speed English, both German voices at 0.5x (pitch preserved)',
        'german_legacy_speed':0.5,
        'german_new_voice':'df_victoria',
        'german_new_speed':0.5,
        'english_speed':1.0,
        'sequence':'English prompt, 2.5s pause, German answer, English example, 2.5s pause, German example',
        'sessions':sessions,
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Finished {len(sessions)} sessions, all >=30 minutes',flush=True)

if __name__=='__main__':main()
