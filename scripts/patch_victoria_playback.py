#!/usr/bin/env python3
"""Update WortFlip's existing UI after all new German MP3s have been generated.
Patches only narrowly identified playback code and cache version; leaves all
card data, ratings, and existing recording files untouched. Idempotent.
"""
from __future__ import annotations

from pathlib import Path
import re
import json
from generate_listening_mp3 import ROOT, GROUP_SOURCES, load_cards


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
    # Device German uses the same half-speed setting, with English unchanged.
    html=replace_or_assert(html,'utterance.rate=.80;', 'utterance.rate=.50;', 'device German speaking rate')
    path.write_text(html,encoding='utf-8')


def patch_long_player():
    path=ROOT/'listening'/'30-minute.html'
    html=path.read_text(encoding='utf-8')
    # The listening UI is a standalone file uploaded with this package.
    # Require it so that we never silently deploy only one of the two voice choices.
    if 'id="voice-source"' not in html or 'id="german-device-voice"' not in html:
        raise ValueError('Upload the NEW listening/30-minute.html from this package to add recorded/device options')
    if 'Device voices use English at 1× and German at 0.5×' not in html:
        raise ValueError('The listening page has an unexpected device-voice configuration')
    # Keep the new page unchanged: it already includes a cache-busted recorded MP3 URL.
    print('Listening player contains both recorded and device voice selections.')


def write_device_cards():
    """Save exact text for the device voice option in long listening sessions."""
    html=(ROOT/'index.html').read_text(encoding='utf-8')
    groups={g:load_cards(html,name) for g,name in GROUP_SOURCES.items()}
    if sum(len(x) for x in groups.values())!=1300:
        raise ValueError('Unexpected card count while preparing device-listening text')
    fields=('en','de','exampleEn','example')
    cards={g:[{field:card[field] for field in fields} for card in rows] for g,rows in groups.items()}
    file=ROOT/'listening'/'30min-device-cards.json'
    file.write_text(json.dumps({'version':1,'cards':cards},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(f'Created device-listening dataset for {sum(len(x) for x in cards.values())} cards.')


def patch_cache():
    path=ROOT/'sw.js'
    text=path.read_text(encoding='utf-8')
    text,count=re.subn(r"const CACHE_NAME = 'wortspiel-pwa-[^']+';", "const CACHE_NAME = 'wortspiel-pwa-v27-dual-source-50pct';",text,count=1)
    if count!=1:raise ValueError('Could not update PWA cache name')
    path.write_text(text,encoding='utf-8')


def main():
    patch_index();patch_long_player();write_device_cards();patch_cache()
    print('Updated individual clips, playback speed, the 30-minute player and PWA cache.')

if __name__=='__main__':main()
