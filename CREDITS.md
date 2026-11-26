# WortFlip — Credits and third-party acknowledgments

**Project:** WortFlip — German Flashcards · Words, Sentences & Listening  
**Creator / maintainer:** Yagmur Kati — [GitHub: @YagmurKati](https://github.com/YagmurKati)  
**Official code repository:** https://github.com/YagmurKati/german-vocabulary-game  
**Play WortFlip:** https://yagmurkati.github.io/german-vocabulary-game/

## German audio

WortFlip's prerecorded pronunciations and German example sentences are generated automatically using these independent third-party tools and resources:

- **Piper text-to-speech (`piper-tts`, version 1.8.0)** — used in GitHub Actions to create audio, not distributed as part of the browser app. The Piper engine is licensed **GPL-3.0-or-later**. Source and legal notices: https://github.com/OHF-Voice/piper1-gpl and https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md
- **Piper German voice `de_DE-thorsten-medium`** — the selected voice model. The voice's [model card](https://huggingface.co/rhasspy/piper-voices/blob/main/de/de_DE/thorsten/medium/MODEL_CARD) states **CC0**. Original Thorsten Voice project: https://github.com/thorstenMueller/Thorsten-Voice
- **FFmpeg / libmp3lame** — used in the audio-generation workflow to encode MP3 files; no FFmpeg binary is embedded in the web app. FFmpeg licensing details: https://ffmpeg.org/legal.html

The audio is **synthetically generated**, not human-recorded, and third-party creators do not necessarily endorse WortFlip. Each project's rights and licenses remain with its owner.

## Hosting and automation

- **GitHub Pages** hosts the website.
- **GitHub Actions** runs the audio-generation workflow.

## Ownership, permitted use, and citation

WortFlip is free to **play** at the public website. That does not itself grant permission to copy, repackage, redistribute, or commercially reuse original application code and learning materials. The app does not currently offer a general open-source license. See [RIGHTS.md](RIGHTS.md).

Citation metadata for publications and teaching materials is in [CITATION.cff](CITATION.cff). Citation is acknowledgment, not a software license.

For permission requests, contact the project maintainer through the [official repository](https://github.com/YagmurKati/german-vocabulary-game).

## Illustrations

The vocabulary illustrations in `images/` were created for WortFlip with AI image generation and curated for the corresponding cards. The Phase 3 package contains 86 distinct images, with selected images reused only for closely related flashcard concepts.
