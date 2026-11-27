#!/usr/bin/env python3
"""Build uninterrupted WortFlip MP3 sessions for four German-only playback rates.

All English prompts/examples are synthesized at the original 100% speed.
All stored German Thorsten and Victoria MP3s remain untouched at 100%.
For screen-locked listening, each speed is rendered as ONE continuous MP3,
with pitch-preserving slowdown applied ONLY to German segments.

Existing 30-minute session divisions are reused to preserve the same cards;
any shorter 100%-speed session receives repeat cards to reach 30 minutes.
Every speed option then uses the same content and card order.
"""
from __future__ import annotations

from bisect import bisect_right
import json
from pathlib import Path
import subprocess

from generate_listening_mp3 import ROOT, GROUP_SOURCES, SAMPLE_RATE, load_cards, get_pcm, silence

SPEEDS=(1.0,0.8,0.6,0.4)
RATE_FOLDER={1.0:'100',0.8:'80',0.6:'60',0.4:'40'}
MIN_SECONDS=1800.0
OUTPUT=ROOT/'listening'/'audio30'/'speeds'
MANIFEST=ROOT/'listening'/'30min-sessions.json'
CLIPS={'lookalikes':('l','y'),'everyday':('e','x'),
       'nouns':('n','z'),'speaking':('s','t'),'verbs':('v','w')}


def audio_file(group,index,example):
    prefix=CLIPS[group][1 if example else 0]
    return ROOT/'audio'/f'{prefix}{index:03d}.mp3'


def tempo_filter(rate):
    if rate==1.0:return None
    if rate==0.4:return 'atempo=0.8,atempo=0.5'
    return f'atempo={rate:g}'


def encoded_german_pcm(group,index,example,rate,cache):
    key=(index,example,rate)
    if key in cache:return cache[key]
    mp3=audio_file(group,index,example)
    if not mp3.is_file() or mp3.stat().st_size<500:
        raise FileNotFoundError(f'Missing recorded German: {mp3}; run Victoria all first')
    args=['ffmpeg','-nostdin','-v','error','-i',str(mp3)]
    effect=tempo_filter(rate)
    if effect:args+=['-af',effect]
    args+=['-f','s16le','-acodec','pcm_s16le','-ar',str(SAMPLE_RATE),'-ac','1','pipe:1']
    result=subprocess.check_output(args)
    if len(result)<100:raise ValueError(f'Could not decode {mp3}')
    cache[key]=result
    return result


def phrase_pcm(voice,text,cache):
    if text not in cache:cache[text]=get_pcm(voice,text)
    return cache[text]


def card_parts(group,index,card,rate,english_voice,german_cache,english_cache):
    return [
      (phrase_pcm(english_voice,card['en'].strip(),english_cache),2.5),
      (encoded_german_pcm(group,index,False,rate,german_cache),0.7),
      (phrase_pcm(english_voice,card['exampleEn'].strip(),english_cache),2.5),
      (encoded_german_pcm(group,index,True,rate,german_cache),1.15),
    ]


def card_duration(group,index,card,rate,voice,german_cache,english_cache):
    return sum(len(x)/(SAMPLE_RATE*2)+gap for x,gap in card_parts(
       group,index,card,rate,voice,german_cache,english_cache))


def build_indices(base,cards,voice,german_cache,english_cache):
    start=int(base['first_card'])-1
    stop=int(base['last_new_card'])
    if not(0<=start<stop<=len(cards)):
        raise ValueError(f'Invalid legacy session range {base["id"]}: {start}, {stop}')
    indices=list(range(start,stop))
    for i in range(int(base.get('repeated_cards',0))):indices.append(i%len(cards))
    group=base['group']
    length=0.5+sum(card_duration(group,i,cards[i],1.0,voice,german_cache,english_cache) for i in indices)
    # The existing session might be shorter than 30 minutes after restoring
    # German to natural speed. Repeat existing cards only, no new vocabulary.
    repeated=int(base.get('repeated_cards',0))
    while length<MIN_SECONDS:
        idx=repeated%len(cards)
        indices.append(idx)
        repeated+=1
        length+=card_duration(group,idx,cards[idx],1.0,voice,german_cache,english_cache)
    return indices,repeated


def render_mp3(base,indices,cards,rate,voice,german_cache,english_cache):
    folder=OUTPUT/RATE_FOLDER[rate]
    folder.mkdir(parents=True,exist_ok=True)
    dest=folder/f'{base["id"]}.mp3'
    args=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
          '-f','s16le','-ar',str(SAMPLE_RATE),'-ac','1','-i','pipe:0',
          '-vn','-codec:a','libmp3lame','-b:a','40k',str(dest)]
    proc=subprocess.Popen(args,stdin=subprocess.PIPE)
    duration=0.5
    starts=[]
    try:
        assert proc.stdin is not None
        proc.stdin.write(silence(0.5))
        for n,idx in enumerate(indices):
            starts.append(round(duration,3))
            for pcm,gap in card_parts(base['group'],idx,cards[idx],rate,voice,german_cache,english_cache):
                proc.stdin.write(pcm)
                proc.stdin.write(silence(gap))
                duration+=(len(pcm)/(SAMPLE_RATE*2)+gap)
            if (n+1)%40==0:
                print(f'  {base["id"]} {RATE_FOLDER[rate]}%: {n+1} cards, {duration/60:.1f}min',flush=True)
        proc.stdin.close()
        code=proc.wait()
        if code:raise RuntimeError(f'ffmpeg exited {code} writing {dest}')
    except BaseException:
        if proc.stdin and not proc.stdin.closed:proc.stdin.close()
        proc.kill();proc.wait()
        dest.unlink(missing_ok=True)
        raise
    if duration<MIN_SECONDS-0.1:raise RuntimeError(f'Session too short: {base["id"]}, rate {rate}, {duration}s')
    if not dest.is_file() or dest.stat().st_size<300000:
        raise RuntimeError(f'Output unexpectedly small: {dest}')
    return {'file':dest.relative_to(ROOT).as_posix(),
            'seconds':round(duration,2),'minutes':round(duration/60,1),
            'card_offsets':starts}


def main():
    from piper import PiperVoice
    html=(ROOT/'index.html').read_text(encoding='utf-8')
    cards={g:load_cards(html,name) for g,name in GROUP_SOURCES.items()}
    if sum(map(len,cards.values()))!=1300:
        raise ValueError('Expected exactly 1300 cards')
    track_manifest=json.loads((ROOT/'audio'/'tracks.json').read_text(encoding='utf-8'))
    coll=track_manifest['collections']
    if len(coll.get('lookalikes',[]))!=500:
        raise ValueError('Generate 1000 missing Victoria clips (all) before rebuilding recorded sessions')
    for group,rows in cards.items():
        for i in range(len(rows)):
            for ex in (False,True):
                f=audio_file(group,i,ex)
                if not f.exists() or f.stat().st_size<500:raise FileNotFoundError(f'Missing {f}')
    existing=json.loads(MANIFEST.read_text(encoding='utf-8'))
    legacy=existing['sessions']
    if not legacy or not all('first_card' in s for s in legacy):
        raise ValueError('Previous session divisions missing; cannot preserve card order')
    en_voice=PiperVoice.load(str((ROOT/'en_US-lessac-medium.onnx').resolve()))
    sessions=[]
    current_group=None
    german_cache={}
    english_cache={}
    for base in legacy:
        group=base['group']
        if group not in cards:raise ValueError(f'Unknown group {group}')
        if group!=current_group:
            german_cache.clear();english_cache.clear();current_group=group
        indices,repeats=build_indices(base,cards[group],en_voice,german_cache,english_cache)
        record={k:base[k] for k in ('id','group','label','first_card','last_new_card')}
        record.update({'cards':len(indices),'repeated_cards':repeats,'speeds':{}})
        for rate in SPEEDS:
            print(f'Rendering {base["id"]}: German {RATE_FOLDER[rate]}%, English 100%',flush=True)
            record['speeds'][RATE_FOLDER[rate]]=render_mp3(base,indices,cards[group],rate,en_voice,german_cache,english_cache)
        # Legacy file field and default seconds permit older apps to continue
        # reading this manifest, but now point to the natural-speed version.
        record['file']=record['speeds']['100']['file']
        record['seconds']=record['speeds']['100']['seconds']
        record['minutes']=record['speeds']['100']['minutes']
        sessions.append(record)
    # Device speech has no dependency on generated recordings.
    fields=('en','de','exampleEn','example')
    device_cards={g:[{key:x[key] for key in fields} for x in rows] for g,rows in cards.items()}
    (ROOT/'listening'/'30min-device-cards.json').write_text(
        json.dumps({'version':1,'cards':device_cards},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    MANIFEST.write_text(json.dumps({
        'version':3,
        'description':'Each listening session has four continuous bilingual MP3 versions; English always 100%',
        'speeds':[100,80,60,40],
        'english_speed':1.0,
        'german_voices':'existing Thorsten and additional Victoria at original source speed',
        'sequence':'English prompt, 2.5s pause, German answer, English example, 2.5s pause, German example',
        'sessions':sessions,
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Generated {len(sessions)*len(SPEEDS)} continuous MP3 files; all 30+ minutes.')

if __name__=='__main__':main()
