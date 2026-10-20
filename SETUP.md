# Idea Catcher — Build Instructions
### (Paste this whole file to Claude and say: "Please set this up for me.")

You are setting up **Idea Catcher** for a new user. It is a personal assistant that captures
every idea they send — typed OR voice — from a private Telegram chat, transcribes the voice ones
for free, auto-sorts them by the user's own labels, and files them into a Notion database.
It runs automatically every hour in the cloud (GitHub Actions), so the user's computer can be off.
**Everything stays on the free tier. No paid APIs, ever.**

Work through the steps below **one at a time, in plain non-technical language.** Never ask the user
to show you a password or token — they paste those into GitHub themselves.

---

## STEP 0 — Explain, then gather their setup
Say, in one line, what you're about to build. Then ask (one question at a time):

1. **"What areas do you want your ideas sorted into?"** (their labels)
   Offer examples: *Personal Instagram, Business Instagram, Admin / Life, Agenda / meetings,
   Content ideas.* Let them pick their own.
2. **"For each area, what keyword will you say at the start of a note to file it there?"**
   Explain the convention: *when you record a voice note or type a message, you start it with a
   keyword and it gets filed under that label automatically.* Examples:
   - "BUSINESS: …" → their Business label
   - "ADMIN: …" → Admin
   - "AGENDA: …" → Agenda
   - no keyword → a default **"Inbox"** label
   Capture this as a simple list: **label → keyword(s).**
3. Confirm they have (help them create any they're missing): a free **Telegram** account, a free
   **Notion** account, a free **GitHub** account.

## STEP 1 — Create their Telegram bot (their capture inbox)
Walk them through **@BotFather** in Telegram: `/newbot` → pick a name → copy the **bot token**
(they keep it private). Have them open a chat with the new bot and send it one message.
Read their **chat ID** from `getUpdates` (or give them a 3-line snippet to run) — they'll need it so
the bot only ever listens to them.

## STEP 2 — Create their Notion database
Create a Notion database called **"Ideas Inbox"** with these properties:
- **Idea** (Title) · **Type** (Select: text / voice / link / photo) · **Project** (Select: *their
  labels from Step 0*) · **Date** · **Status** (Select: New / Processed) · **Source** (Select:
  Telegram).
Create a **Notion integration**, share the database with it, and note the **Notion token** +
**database ID**.

## STEP 3 — Build the pipeline (the free "server")
1. Create a new **private GitHub repo** for them (e.g. `idea-catcher`).
2. Copy the files from this kit's **`/templates`** folder into it: `pull_to_notion.py`,
   `requirements.txt`, `.github/workflows/ideas.yml`.
3. In `pull_to_notion.py`, fill the **`LABELS`** config at the top with their label → keyword list
   from Step 0, and set their Notion property names if they renamed any.
4. Add their secrets under **GitHub → Settings → Secrets and variables → Actions**:
   `TELEGRAM_BOT_TOKEN`, `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `ALLOWED_CHAT_ID`.
5. The workflow is already set to run **hourly**, transcribe voice notes with **local Whisper**
   (free), and includes a **cost guard** that warns them and stops before they could ever be billed.

## STEP 4 — Test it together
Have them send one voice note to the bot. Run the workflow once manually
(**Actions tab → Run workflow**) to confirm it transcribes and files correctly under the right
label. After that it's fully automatic, every hour, hands-free.

---

## Hard rules (keep it free + safe)
- **Free tier only:** local Whisper (never a paid transcription API), GitHub free minutes, free
  Notion, free Telegram.
- **Never see or print their tokens.** They paste them into GitHub secrets.
- **The bot listens only to them** (via `ALLOWED_CHAT_ID`).
- **Judgment stays in chat:** priority / next-action / notes are filled later by the user or an
  assistant in a normal chat — NOT automated in the cloud (that would need a paid AI API). The
  cloud job only *captures, transcribes, sorts, and files.*
