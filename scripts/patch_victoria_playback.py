#!/usr/bin/env python3
"""Update WortFlip's existing UI after all new German MP3s have been generated.
Patches only narrowly identified playback code and cache version; leaves all
card data, ratings, and existing recording files untouched. Idempotent.
"""
from __future__ import annotations

from pathlib import Path
import re
from generate_listening_mp3 import ROOT


def replace_or_assert(source, old, new, label):
    if new in source:
        return source
    count=source.count(old)
    if count!=1:
        raise ValueError(f'Cannot safely patch {label}: expected 1 target, found {count}')
    return source.replace(old,new,1)


def patch_index():
    path=ROOT/'index.html'
    html=path.read_text(encoding='utf-8')
    old="function canPlayRecording(){return queue.length>0&&cursor<queue.length&&((library==='lookalikes'&&queue[cursor]<400)||(library==='everyday'&&queue[cursor]<400));}"
    new="function canPlayRecording(){return queue.length>0&&cursor<queue.length;}"
    html=replace_or_assert(html,old,new,'enable recordings for all 1300 cards')
    old="if(d.version!==1||d.collections.lookalikes.length!==400||d.collections.everyday.length!==400||d.collections.examples.length!==400||!Array.isArray(d.collections.lookalike_examples)||d.collections.lookalike_examples.length!==400)throw Error('The audio track list is incomplete');"
    new="if(d.version!==1||!d.collections||Object.entries({lookalikes:500,everyday:400,examples:400,lookalike_examples:500,nouns:200,noun_examples:200,speaking:100,speaking_examples:100,verbs:100,verb_examples:100}).some(([key,n])=>!Array.isArray(d.collections[key])||d.collections[key].length!==n))throw Error('The audio track list is incomplete');"
    html=replace_or_assert(html,old,new,'audio manifest validation')
    old="const prefix=example?(library==='lookalikes'?'y':'x'):(library==='lookalikes'?'l':'e');\n const file='audio/'+prefix+String(idx).padStart(3,'0')+'.mp3';"
    new="""let prefix, localIndex=idx;
 if(library==='lookalikes')prefix=example?'y':'l';
 else if(idx<400)prefix=example?'x':'e';
 else if(idx<600){prefix=example?'z':'n';localIndex=idx-400;}
 else if(idx<700){prefix=example?'t':'s';localIndex=idx-600;}
 else{prefix=example?'w':'v';localIndex=idx-700;}
 const file='audio/'+prefix+String(localIndex).padStart(3,'0')+'.mp3';"""
    html=replace_or_assert(html,old,new,'individual German clip mapping')
    old="const player=new Audio();\n recordingPlayer=player;"
    new="""const player=new Audio();
 // Both German voices (existing Thorsten and new Victoria) play at half speed.
 player.playbackRate=0.5;
 player.preservesPitch=true;
 recordingPlayer=player;"""
    html=replace_or_assert(html,old,new,'individual male playback speed')
    path.write_text(html,encoding='utf-8')


def patch_long_player():
    path=ROOT/'listening'/'30-minute.html'
    html=path.read_text(encoding='utf-8')
    old='<label for="speed">Playback speed</label>'
    new='<label for="speed">Overall playback speed (both languages)</label>'
    html=replace_or_assert(html,old,new,'overall playback label')
    note='''<p class="note" id="german-pace-note"><strong>English is at its original speed.</strong>
 Existing male German recordings are 50% slower (half speed), with pitch preserved;
 new Victoria German clips are also 50% slower (half speed). Overall playback speed
 changes both languages, so leave it at Normal (1×).</p>'''
    if 'id="german-pace-note"' in html:
        # Replace any prior 20%-slower note with a truthful new one.
        html,count=re.subn(r'<p class="note" id="german-pace-note">.*?</p>',note,html,count=1,flags=re.S)
        if count!=1: raise ValueError('Could not update old pace note')
    else:
        needle='<label class="check"><input type="checkbox" id="repeat">'
        html=replace_or_assert(html,needle,note+'\n'+needle,'new pace note')
    # Invalidate old audio30 URLs even on devices with persistent saved MP3s.
    old='const url = new URL(s.file, base).href;'
    new="const url = new URL(s.file, base).href + '?voices=victoria-and-thorsten-50pct-v1';"
    html=replace_or_assert(html,old,new,'long MP3 cache bust')
    path.write_text(html,encoding='utf-8')


def patch_cache():
    path=ROOT/'sw.js'
    text=path.read_text(encoding='utf-8')
    text,count=re.subn(r"const CACHE_NAME = 'wortspiel-pwa-[^']+';", "const CACHE_NAME = 'wortspiel-pwa-v26-victoria-50pct';",text,count=1)
    if count!=1:raise ValueError('Could not update PWA cache name')
    path.write_text(text,encoding='utf-8')


def main():
    patch_index();patch_long_player();patch_cache()
    print('Updated individual clips, playback speed, the 30-minute player and PWA cache.')

if __name__=='__main__':main()
