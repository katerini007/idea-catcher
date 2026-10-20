#!/usr/bin/env python3
"""
Idea Catcher — pulls new Telegram ideas into a Notion database.

Runs hourly on GitHub Actions (free). Transcribes voice notes locally with
Whisper (free), sorts each idea by the user's keyword, and files it in Notion.
Secrets come from environment variables (GitHub injects them); nothing sensitive
lives in this file. A monthly cost guard keeps it inside GitHub's free tier.

================================  EDIT THIS  ================================
Fill LABELS with the user's areas and the keyword(s) that file a note there.
First match wins, so put the most specific labels first. A note with no keyword
goes to DEFAULT_LABEL. BRAND_WORDS just helps Whisper spell names correctly.
"""
LABELS = {
    # "Label shown in Notion": ["keyword", "another keyword (lowercase)"],
    "Business":  ["business", "biz", "work"],
    "Personal":  ["personal", "life"],
    "Admin":     ["admin", "admso", "paperwork"],
    "Agenda":    ["agenda", "meeting", "calendar"],
    "Content":   ["content", "reel", "post", "idea"],
}
DEFAULT_LABEL = "Inbox"
BRAND_WORDS = ""   # e.g. "Acme Studio, Jane Doe" — names you want spelled right
# Notion property names (change only if you renamed them in your database):
PROP_TITLE, PROP_TYPE, PROP_PROJECT = "Idea", "Type", "Project"
PROP_DATE, PROP_STATUS, PROP_SOURCE = "Date", "Status", "Source"
# ===========================================================================

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
NOTION_DB = os.environ.get("NOTION_DATABASE_ID", "").strip()
ALLOWED_CHAT_ID = os.environ.get("ALLOWED_CHAT_ID", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
OFFSET_FILE = HERE / "pull_offset.json"

# --- cost guard (keeps GitHub Actions usage inside the free tier) ------------
GUARD_FILE = HERE / "usage_guard.json"
EST_MIN_PER_RUN = 1.5
FREE_MINUTES = 2000
WARN_AT, HARD_AT = 1600, 1900


def classify(text):
    low = (text or "").lower()
    for label, words in LABELS.items():
        if any(w in low for w in words):
            return label
    return DEFAULT_LABEL


def detect_type(msg):
    if "voice" in msg or "audio" in msg:
        return "voice"
    if "photo" in msg:
        return "photo"
    if "document" in msg:
        return "file"
    text = msg.get("text") or msg.get("caption") or ""
    return "link" if ("http://" in text or "https://" in text or "t.me/" in text) else "text"


def load_offset():
    if OFFSET_FILE.exists():
        try:
            return json.loads(OFFSET_FILE.read_text()).get("offset", 0)
        except Exception:
            return 0
    return 0


def save_offset(o):
    OFFSET_FILE.write_text(json.dumps({"offset": o}))


def tg_send(text):
    if not (TOKEN and ALLOWED_CHAT_ID):
        return
    try:
        requests.post(f"{API}/sendMessage",
                      json={"chat_id": ALLOWED_CHAT_ID, "text": text}, timeout=15)
    except Exception as e:
        print(f"[tg] warn send failed: {e}")


def load_guard():
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    g = {"month": month, "runs": 0, "warned": False}
    if GUARD_FILE.exists():
        try:
            cur = json.loads(GUARD_FILE.read_text())
            if cur.get("month") == month:
                g = cur
        except Exception:
            pass
    g["runs"] = int(g.get("runs", 0)) + 1
    return g


def save_guard(g):
    GUARD_FILE.write_text(json.dumps(g))


_WHISPER = None


def _get_whisper():
    global _WHISPER
    if _WHISPER is None:
        from faster_whisper import WhisperModel
        _WHISPER = WhisperModel(os.environ.get("WHISPER_MODEL", "small"),
                                device="cpu", compute_type="int8")
    return _WHISPER


def transcribe_voice(file_id):
    """Download a Telegram voice note and transcribe it locally (free). On any
    failure, fall back to a placeholder so the pull never breaks."""
    placeholder = f"[voice note — transcription pending | file_id={file_id}]"
    if not file_id:
        return "[voice note — no file]"
    try:
        import tempfile
        gf = requests.get(f"{API}/getFile", params={"file_id": file_id}, timeout=30).json()
        if not gf.get("ok"):
            return placeholder
        fpath = gf["result"]["file_path"]
        ext = os.path.splitext(fpath)[1] or ".oga"
        audio = requests.get(f"{API.replace('/bot', '/file/bot')}/{fpath}", timeout=120)
        audio.raise_for_status()
        tmp = Path(tempfile.gettempdir()) / f"tgvoice_{file_id[:10]}{ext}"
        tmp.write_bytes(audio.content)
        segs, _ = _get_whisper().transcribe(
            str(tmp), vad_filter=True,
            initial_prompt=BRAND_WORDS or None)
        text = " ".join(s.text.strip() for s in segs).strip()
        try:
            tmp.unlink()
        except Exception:
            pass
        return text or f"[voice note — no speech detected | file_id={file_id}]"
    except Exception as e:
        print(f"[transcribe] failed: {e}")
        return placeholder


def save_to_notion(idea):
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}",
               "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
    payload = {"parent": {"database_id": NOTION_DB}, "properties": {
        PROP_TITLE:   {"title": [{"text": {"content": idea["text"][:2000] or "(no text)"}}]},
        PROP_TYPE:    {"select": {"name": idea["type"]}},
        PROP_PROJECT: {"select": {"name": idea["project"]}},
        PROP_DATE:    {"date": {"start": idea["date"]}},
        PROP_STATUS:  {"select": {"name": "New"}},
        PROP_SOURCE:  {"select": {"name": "Telegram"}},
    }}
    r = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=20)
    if r.status_code != 200:
        print(f"[notion] save failed {r.status_code}: {r.text[:300]}")
        return False
    return True


def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN missing")
    if not (NOTION_TOKEN and NOTION_DB):
        raise SystemExit("NOTION_TOKEN / NOTION_DATABASE_ID missing")

    guard = load_guard()
    est_min = guard["runs"] * EST_MIN_PER_RUN
    skip_transcribe = False
    if est_min >= HARD_AT:
        tg_send(f"⚠️ Idea Catcher: ~{int(est_min)}/{FREE_MINUTES} free GitHub minutes used this "
                f"month. Skipping runs until next month so you're NEVER charged.")
        save_guard(guard)
        print(f"[guard] est {est_min} min >= hard cap; skipping run.")
        return
    if est_min >= WARN_AT:
        skip_transcribe = True
        if not guard.get("warned"):
            tg_send(f"⚠️ Idea Catcher: ~{int(est_min)}/{FREE_MINUTES} free GitHub minutes used this "
                    f"month. Pausing voice transcription to stay 100% free (text still saved).")
            guard["warned"] = True

    offset = load_offset()
    updates = requests.get(f"{API}/getUpdates",
                           params={"offset": offset, "timeout": 10}, timeout=30).json().get("result", [])
    saved, commit_offset = 0, offset
    for u in updates:
        uid = u["update_id"]
        msg = (u.get("message") or u.get("edited_message")
               or u.get("channel_post") or u.get("edited_channel_post"))
        if not msg:
            commit_offset = uid + 1
            continue
        if ALLOWED_CHAT_ID and str(msg.get("chat", {}).get("id", "")) != ALLOWED_CHAT_ID:
            commit_offset = uid + 1
            continue
        itype = detect_type(msg)
        text = (msg.get("text") or msg.get("caption") or "").strip()
        if itype == "voice":
            fid = (msg.get("voice") or msg.get("audio") or {}).get("file_id", "")
            transcript = (f"[voice note — transcription pending | file_id={fid}]"
                          if skip_transcribe else transcribe_voice(fid))
            text = (text + " " + transcript).strip()
        elif itype == "photo" and not text:
            text = "[photo idea — no caption]"
        idea = {"text": text, "type": itype, "project": classify(text),
                "date": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if save_to_notion(idea):
            saved += 1
            commit_offset = uid + 1
        else:
            print("[notion] save failed — stopping so this message retries next run")
            break

    save_offset(commit_offset)
    save_guard(guard)
    print(f"Saved {saved} idea(s). Offset {commit_offset}. Run {guard['runs']} (~{int(est_min)}/{FREE_MINUTES} min).")


if __name__ == "__main__":
    main()
