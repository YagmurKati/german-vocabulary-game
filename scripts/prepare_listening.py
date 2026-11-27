#!/usr/bin/env python3
"""Publish device-listening card text and add selectable German-only speeds.

Safe to run before Victoria audio generation. Changes no vocabulary data,
progress values, or prerecorded MP3s. Re-run after Victoria's `all` to enable
new clips on flashcards. All mutations are idempotent.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from generate_listening_mp3 import ROOT, GROUP_SOURCES, load_cards

SPEEDS = ("1", "0.8", "0.6", "0.4")
SPEED_KEY = "wortflip-german-speed-v1"


def patch_flashcards(html: str, complete: bool) -> str:
    if 'id="german-speed"' not in html:
        anchor = ' <button type="button" id="audio-download-btn"'
        control = ''' <label for="german-speed">German speaking speed (English stays normal)</label>
 <select id="german-speed" aria-label="German voice playback speed">
  <option value="1" selected>100% · Normal</option>
  <option value="0.8">80% · 20% slower</option>
  <option value="0.6">60% · 40% slower</option>
  <option value="0.4">40% · 60% slower</option>
 </select>
'''
        if html.count(anchor) != 1:
            raise ValueError('Could not locate unique flashcard audio settings')
        html = html.replace(anchor, control + anchor, 1)

    if 'const GERMAN_SPEED_PREF_KEY=' not in html:
        anchor = 'function playRecorded(example=false){'
        preamble = '''const GERMAN_SPEED_PREF_KEY='wortflip-german-speed-v1';
const germanSpeedSelect=el('german-speed');
try {
 const saved=localStorage.getItem(GERMAN_SPEED_PREF_KEY);
 if(['1','0.8','0.6','0.4'].includes(saved)) germanSpeedSelect.value=saved;
} catch(e) {}
function germanPlaybackSpeed(){return Number(germanSpeedSelect.value)||1;}
germanSpeedSelect.addEventListener('change',()=>{
 try {localStorage.setItem(GERMAN_SPEED_PREF_KEY,germanSpeedSelect.value);}catch(e){}
 if(recordingPlayer) recordingPlayer.playbackRate=germanPlaybackSpeed();
});
'''
        if html.count(anchor) != 1:
            raise ValueError('Could not locate unique flashcard recording function')
        html = html.replace(anchor, preamble + anchor, 1)

    # The recorded audio object is exclusive to German clips in flashcard mode.
    html, n = re.subn(r"const player=new Audio\(\);\s*(?://[^\n]*\n\s*)?player\.playbackRate=0\.5;\s*player\.preservesPitch=true;\s*recordingPlayer=player;",
                      "const player=new Audio();\n player.playbackRate=germanPlaybackSpeed();\n player.preservesPitch=true;\n recordingPlayer=player;", html, count=1)
    if not n:
        anchor='const player=new Audio();\n recordingPlayer=player;'
        if anchor not in html and 'player.playbackRate=germanPlaybackSpeed()' not in html:
            raise ValueError('Could not locate recorded German audio playback')
        html=html.replace(anchor,"const player=new Audio();\n player.playbackRate=germanPlaybackSpeed();\n player.preservesPitch=true;\n recordingPlayer=player;",1)
    html=html.replace('utterance.rate=.80;', 'utterance.rate=germanPlaybackSpeed();')
    html=html.replace('utterance.rate=.50;', 'utterance.rate=germanPlaybackSpeed();')

    if complete:
        html=re.sub(r"function canPlayRecording\(\)\{return queue\.length>0&&cursor<queue\.length&&\(\(library==='lookalikes'&&queue\[cursor\]<400\)\|\|\(library==='everyday'&&queue\[cursor\]<400\)\);\}",
                    'function canPlayRecording(){return queue.length>0&&cursor<queue.length;}',html,count=1)
        old = "const prefix=example?(library==='lookalikes'?'y':'x'):(library==='lookalikes'?'l':'e');\n const file='audio/'+prefix+String(idx).padStart(3,'0')+'.mp3';"
        new = """let prefix, localIndex=idx;
 if(library==='lookalikes')prefix=example?'y':'l';
 else if(idx<400)prefix=example?'x':'e';
 else if(idx<600){prefix=example?'z':'n';localIndex=idx-400;}
 else if(idx<700){prefix=example?'t':'s';localIndex=idx-600;}
 else{prefix=example?'w':'v';localIndex=idx-700;}
 const file='audio/'+prefix+String(localIndex).padStart(3,'0')+'.mp3';"""
        if old in html:html=html.replace(old,new,1)
        elif new not in html:raise ValueError('Cannot update per-card MP3 mapping safely')
        old_validation = "if(d.version!==1||d.collections.lookalikes.length!==400||d.collections.everyday.length!==400||d.collections.examples.length!==400||!Array.isArray(d.collections.lookalike_examples)||d.collections.lookalike_examples.length!==400)throw Error('The audio track list is incomplete');"
        new_validation = "if(d.version!==1||!d.collections||Object.entries({lookalikes:500,everyday:400,examples:400,lookalike_examples:500,nouns:200,noun_examples:200,speaking:100,speaking_examples:100,verbs:100,verb_examples:100}).some(([key,n])=>!Array.isArray(d.collections[key])||d.collections[key].length!==n))throw Error('The audio track list is incomplete');"
        if old_validation in html:html=html.replace(old_validation,new_validation,1)
        elif new_validation not in html:raise ValueError('Cannot update recorded audio manifest check safely')
    return html


def main():
    index=ROOT/'index.html'
    html=index.read_text(encoding='utf-8')
    sources={g:load_cards(html,c) for g,c in GROUP_SOURCES.items()}
    if sum(len(x) for x in sources.values()) != 1300:
        raise ValueError('Expected exactly 1300 existing cards')
    fields=('en','de','exampleEn','example')
    cards={g:[{key:x[key] for key in fields} for x in rows] for g,rows in sources.items()}
    output=ROOT/'listening'/'30min-device-cards.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'version':1,'cards':cards},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    manifest=json.loads((ROOT/'audio'/'tracks.json').read_text(encoding='utf-8'))
    coll=manifest['collections']
    complete=(len(coll.get('lookalikes',[]))==500 and all(len(coll.get(k,[]))==n for k,n in {
        'lookalike_examples':500,'nouns':200,'noun_examples':200,
        'speaking':100,'speaking_examples':100,'verbs':100,'verb_examples':100}.items()))
    html=patch_flashcards(html,complete)
    index.write_text(html,encoding='utf-8')
    sw=ROOT/'sw.js'
    s=sw.read_text(encoding='utf-8')
    s,n=re.subn(r"const CACHE_NAME = 'wortspiel-pwa-[^']+';", "const CACHE_NAME = 'wortspiel-pwa-v30-four-speed-german';",s,count=1)
    if n!=1: raise ValueError('Could not find PWA cache name')
    sw.write_text(s,encoding='utf-8')
    print('Published 1300 device-listening cards and 4-speed flashcard controls.')
    print('All new Victoria clips present:',complete)

if __name__=='__main__':main()
