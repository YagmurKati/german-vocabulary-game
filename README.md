# WortFlip ✦ — German Flashcards · Words, Sentences & Listening

**Free German vocabulary flashcards for everyday speaking and listening (roughly B1–B2).**

### ▶ [Open WortFlip — Play online](https://yagmurkati.github.io/german-vocabulary-game/)

WortFlip is a simple, installable web app with **800 English-to-German flashcards** organized into two separate libraries:

- **English Lookalikes (400 words):** German words that resemble English words, with German example sentences, English translations, pronunciation and usage notes where helpful.
- **Everyday German (400 words and expressions):** Practical phrases for transportation, appointments, shopping, home, work, conversations, health and other everyday situations. Cards start in English, reveal the German answer, and include bilingual example sentences with pronunciation.

English Lookalikes are grouped in four successive 100-word sets, from most recognizable to broader vocabulary. Both libraries have an optional estimated CEFR level filter (A1–A2, B1, B2, C1). The levels are practical approximations, not official certifications.

Choose a category, reveal the German answer, and mark what you know or need to practice again. You can review difficult cards and listen to German pronunciation using voices available on your device.

## Install on your phone — free

You do **not** need Google Play or the Apple App Store. WortFlip is a **Progressive Web App (PWA)** you can add directly to your phone's home screen.

### Android (Chrome)

1. Open **[WortFlip](https://yagmurkati.github.io/german-vocabulary-game/)** in Chrome.
2. Tap the **⋮** menu.
3. Select **Install app**, **Install and create shortcut**, or **Add to Home screen** (the wording varies).
4. Choose **Install**. The WortFlip icon should appear on your home screen. Already-installed copies may keep their old label until your phone refreshes the installed app metadata.

If Chrome offers only **Create shortcut**, make sure the latest app files have been published, reload the website, and try again. A shortcut opens the game in Chrome but is not the same as a standalone PWA installation.

### iPhone (Safari)

1. Open **[WortFlip](https://yagmurkati.github.io/german-vocabulary-game/)** in **Safari**.
2. Tap **Share** (sometimes via the page menu), then **Add to Home Screen**.
3. Turn on **Open as Web App** if you see it, then tap **Add**.
4. Launch WortFlip from your home screen.

If you don't see **Add to Home Screen**, scroll to the bottom of Safari's share sheet and use **Edit Actions** to enable it. Instructions may vary slightly by iOS version. See [Apple's official instructions](https://support.apple.com/guide/iphone/bookmark-a-website-iph42ab2f3a/ios).

### Use it offline

Open WortFlip online once to cache the app. Flashcards then work offline subject to browser storage. To play **recorded audio** offline too, use the in-game **Save all German audio for offline use** feature while online.

## Consistent German pronunciation

WortFlip offers a **Recorded German voice** option. Once the audio generation is finished, the **same MP3 recordings** play on macOS, Windows, Android and iPhone. The recording source does not change depending on your device. You can also choose your device's German voice manually, if you prefer.

The recordings use the German **Piper `de_DE-thorsten-medium`** neural TTS model. They are synthetic, not reviewed native-speaker recordings. A few loanwords or names may still sound unusual. For important words, check a reliable dictionary with native-speaker audio; a corrected recording can replace an individual MP3 in `audio/`.

### Generate the recordings once (repository maintainer)

After uploading the package, open the GitHub repo's **Actions** tab, select **Generate consistent German pronunciation recordings**, then run it in **preview** mode first to listen to 10 sample clips. If they sound suitable, run the workflow in **all** mode. That creates and publishes 1,600 MP3s: 800 words/phrases plus 800 German example sentences. The game automatically plays them after the website has rebuilt. If the workflow-generated commit does not trigger GitHub Pages to update, make a small manual README commit. See `.github/workflows/generate-german-audio.yml` for the audio-generation workflow.

### Save German audio for offline listening

Open the game online, choose **Recorded German voice** and click **Save all German audio for offline use** while connected to Wi-Fi. Keep the app open until all tracks are cached. This can take several minutes and uses additional local storage. Your browser may erase cached files if storage is low. Audio tracks you've already played are usually cached individually.

## Learning progress and privacy

Progress and voice preference are saved **locally in your browser on your device**. There is no account, and progress is **not automatically synchronized** across phones, computers or browsers.

Use **Save backup** and **Restore** in the game to transfer your progress to another device or back it up before clearing browser data. Clearing browser/site data can erase local progress. Installing a PWA on iOS may use storage separate from Safari, so keep a backup when switching between the website and the home-screen app.

## Credits, citation, and rights

- [Third-party acknowledgments](CREDITS.md)
- [How to cite WortFlip](CITATION.cff) (GitHub shows **Cite this repository**)
- The original WortFlip application code and educational content have **no open-source license granted**. See [RIGHTS.md](RIGHTS.md). Third-party tools and voice models remain subject to their own licenses.
- The project remains available at its original GitHub repository and GitHub Pages URL to preserve existing links and browser-stored learning progress. The internal `wortspiel-*` keys are intentionally retained for compatibility.

## About this project

WortFlip is a small, free educational project hosted using [GitHub Pages](https://pages.github.com/). The game works in modern browsers on desktop and mobile. It focuses on active recall: **see English → try to say German → reveal the answer → mark your result**.

**Play now:** https://yagmurkati.github.io/german-vocabulary-game/
