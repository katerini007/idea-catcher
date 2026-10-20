# Idea Catcher — how it works (the detailed version)

## In one sentence
A Telegram bot captures your messages, a free scheduled job in the cloud reads them, transcribes any
voice notes with local AI (Whisper), sorts them by your keywords, and writes them into your Notion
database — hands-free, on the free tier.

## The three pieces
1. **Telegram — your capture inbox.** You send ideas to your own private bot. It's the fastest way
   to catch a thought, especially by voice. The bot only ever listens to *you*.
2. **GitHub Actions — the free "server."** A job runs every hour on GitHub's computers (not yours).
   Each run it:
   - fetches any new messages from your bot,
   - **transcribes voice notes locally with Whisper** (open-source, free),
   - **tags each idea by the keyword** you used at the start,
   - **saves it to Notion** as a new row.
3. **Notion — your organised brain.** Every idea lands here, written out and sorted, ready to act on.

## Why it's genuinely free
- Voice transcription uses **Whisper**, which runs on the free GitHub machine — not a paid
  transcription service.
- GitHub gives **2,000 free minutes/month**; this uses a small fraction (it runs hourly and only
  spends real time when there's actually a voice note).
- A built-in **cost guard** tracks usage, messages you on Telegram as you approach the free limit,
  pauses transcription to stay free, and hard-stops before you could ever be charged. (GitHub's own
  default spending limit is also €0, so a surprise bill is impossible unless you opt in.)

## What it fills in automatically vs. what you decide
- **Automatic (cloud, free):** the idea text (including the transcript), its type (voice/text/link),
  its label (from your keyword), the date, and a "New" status.
- **Your call (later, on demand, free):** priority, the next action, deeper notes. This is *judgment*,
  so it's done by you — or an assistant in a normal chat — not automated in the cloud. Automating
  judgment would need a paid AI service; keeping it in chat keeps it free and smarter.

## Privacy & safety
- Your bot responds only to your own chat ID.
- Your tokens live in **GitHub's encrypted secrets** — never written into the code or shared.
- Each customer runs their **own** private copy; nothing is shared between users.

## The flow, at a glance
```
You (voice/text in Telegram)
        │
        ▼
Telegram bot  ──hourly──►  GitHub Actions job
                               │  • transcribe voice (Whisper, free)
                               │  • sort by your keyword
                               ▼
                           Notion "Ideas Inbox"  →  you act on it
```
