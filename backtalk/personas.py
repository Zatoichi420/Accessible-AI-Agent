# Characters and accessibility settings, added on top of backtalk.
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Characters and the user's accessibility profile.

One brain, several faces. A character is a personality file
(personas/<id>.md), a voice, and a few defaults (personas/personas.json).
personas/_core.md holds the respect and accessibility rules every
character follows. The user's settings live under "profile" in
backtalk.json and override a character's defaults.

Switching and settings changes are matched in CODE from exact spoken
phrases (like "talk slower"), never left to the model to play along.
The prompt is rebuilt and the brain reconnects to the SAME conversation,
so the new character remembers everything.
"""
import json
import re
from pathlib import Path

from backtalk.config import CFG, REPO
from backtalk.vlog import log

PERSONAS_DIR = REPO / "personas"
REGISTRY_PATH = PERSONAS_DIR / "personas.json"
# Everything the active character is, in one file, for sessions that
# don't go through the voice app (typed chat, the phone bridge). Their
# CLAUDE.md points here.
ACTIVE_FILE = REPO / "state" / "active-character.md"

PROFILE_DEFAULTS = {
    "character": "data",
    "screen_reader": "voiceover",
    "detail_level": None,        # None = the character's default
    "narrate_actions": True,
    "read_errors_exactly": True,
    "image_description": "full",
    "earcons": True,
    "swearing": None,
    "humor": None,
    "encouragement": None,
    "call_me": None,
    # Free text about the user (name, setup, interests) for the prompt.
    "user_name": "",
    "about_me": "",
}

DETAIL_TEXT = {
    "brief": "BRIEF: one or two sentences. What it is and the one thing "
             "that matters. Offer more in a few words if there is more.",
    "standard": "STANDARD: a few sentences. What it is, the main parts in "
                "reading order, what is focused or selected, what changed.",
    "descriptive": "DESCRIPTIVE: give the count and the main point first, "
                   "then full detail: layout, every control with its label "
                   "and state, all visible text, colors and visual style "
                   "when relevant, what changed, and what to press next.",
}
SWEARING_TEXT = {
    "off": "Do not swear.",
    "mild": "Light, occasional swearing is fine.",
    "full": "Swear freely, in character.",
}
READERS = {"voiceover": "VoiceOver (VO = Control+Option)",
           "nvda": "NVDA (NVDA key = Insert or Caps Lock)",
           "jaws": "JAWS (JAWS key = Insert)",
           "talkback": "TalkBack (Android gestures)"}


def _load_registry() -> dict:
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except (OSError, ValueError) as e:
        log(f"[personas] registry unreadable ({e}); characters disabled")
        return {}


REGISTRY = _load_registry()
ENABLED = bool(REGISTRY)


def profile() -> dict:
    p = dict(PROFILE_DEFAULTS)
    p.update({k: v for k, v in (CFG.get("profile") or {}).items()})
    if p["character"] not in REGISTRY and REGISTRY:
        p["character"] = next(iter(REGISTRY))
    return p


def active_id() -> str:
    return profile()["character"]


def active() -> dict:
    return REGISTRY.get(active_id(), {})


def effective(key: str):
    """A setting's value: the user's profile if set, else the character's
    default."""
    v = profile().get(key)
    if v is None:
        v = active().get("defaults", {}).get(key)
    if key == "call_me" and v is None:
        v = active().get("call_me", "")
    if isinstance(v, str):
        v = _fill(v)
    return v


def _fill(text: str) -> str:
    """Fill {user_name}; with no name set, the placeholder and the
    punctuation after it simply drop out."""
    name = str((CFG.get("profile") or {}).get("user_name") or "")
    if name:
        return text.replace("{user_name}", name)
    return re.sub(r"\{user_name\}[.,]?\s*", "", text).strip()


def _read(name: str) -> str:
    try:
        return (PERSONAS_DIR / name).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def build_prompt() -> str:
    """The character block appended to the system prompt."""
    if not ENABLED:
        return ""
    p = active()
    reader = READERS.get(str(effective("screen_reader")).lower(),
                         str(effective("screen_reader")))
    detail = str(effective("detail_level") or "standard")
    others = ", ".join(v["name"] for k, v in REGISTRY.items()
                       if k != active_id())
    settings = [
        f"Screen reader in use: {reader}.",
        f"Detail level: {DETAIL_TEXT.get(detail, detail)}",
        f"Swearing: {SWEARING_TEXT.get(str(effective('swearing')), 'Do not swear.')}",
        f"Humor, 0 to 3: {effective('humor')}.",
        f"Encouragement: {effective('encouragement')} (always specific "
        "and true, never empty praise).",
        f"Call the user: {effective('call_me') or 'nothing in particular'}.",
        ("Narrate actions: say what you are about to do, then what "
         "actually happened." if effective("narrate_actions") else
         "Narrate actions: off; report results only."),
        ("Read errors exactly, word for word, then explain."
         if effective("read_errors_exactly") else ""),
        f"Image and screen descriptions: {effective('image_description')}.",
    ]
    return "\n\n".join(x for x in (
        "CHARACTER (set by the voice app; this OVERRIDES any name, "
        "character, voice or welcome line described in CLAUDE.md. Every "
        "rule in CLAUDE.md about safety, memory and work still applies). "
        f"You are {p.get('name')}. The user can switch to: {others}, by "
        "saying 'switch to' and the name; that is handled by the voice "
        "app, not you. Stay fully in character.",
        _read("_core.md"),
        ("ABOUT THE USER: " + " ".join(x for x in (
            f"Name: {profile()['user_name']}." if profile()["user_name"]
            else "", str(profile()["about_me"] or "")) if x))
        if (profile()["user_name"] or profile()["about_me"]) else "",
        _read(f"{active_id()}.md"),
        "CURRENT SETTINGS (override the character's defaults):\n- "
        + "\n- ".join(s for s in settings if s),
    ) if x)


def apply_voice():
    """Point the mouth at the active character's voice. Runtime-only
    keys (underscore), so nothing here is ever saved over the user's
    configured voice."""
    if not ENABLED:
        return
    p = active()
    CFG["_kokoro_voice"] = p.get("kokoro_voice") or CFG.get("voice")
    CFG["_el_voice"] = p.get("elevenlabs_voice_id", "")


def write_active_file():
    """Mirror the active character for non-voice sessions. Never raises."""
    if not ENABLED:
        return
    try:
        ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_FILE.write_text(
            "# Active character (written by the voice app; do not edit)\n\n"
            + build_prompt() + "\n", encoding="utf-8")
    except OSError as e:
        log(f"[personas] could not write {ACTIVE_FILE.name}: {e}")


def greeting() -> str:
    return _fill(active().get("greeting", ""))


def signoff() -> str:
    return _fill(active().get("signoff", ""))


def all_names() -> list[str]:
    return [v["name"] for v in REGISTRY.values()]


def roster_line() -> str:
    names = all_names()
    return (f"{len(names)} characters: " + ", ".join(names[:-1])
            + f", and {names[-1]}. {active().get('name')} is on now. "
            "Say switch to, and a name.")


# --- spoken commands ---------------------------------------------------

def _norm(text: str) -> str:
    t = text.lower().replace("-", " ").replace(".", " ").replace(",", " ")
    return " ".join(t.split()).strip(" !?")


_SWITCH = re.compile(
    r"^(?:(?:please )?(?:switch|change|swap) (?:over )?to|bring (?:up|in|out)|"
    r"put|talk to|give me|let me talk to|i want)\s+(.+?)"
    r"(?:\s+on|\s+please|\s+now)*$")
_TAKE_OVER = re.compile(r"^(.+?)\s+(?:take over|you(?:'re| are) up|take the con)$")


def match_switch(text: str):
    """Persona id for a switch command, or None."""
    if not ENABLED:
        return None
    n = _norm(text)
    m = _SWITCH.match(n) or _TAKE_OVER.match(n)
    if not m:
        return None
    who = m.group(1).strip()
    for pid, p in REGISTRY.items():
        if who in p.get("aliases", []) or who == pid:
            return pid
    return None


ROSTER_PHRASES = ("list characters", "list the characters",
                  "who's available", "who is available",
                  "who can i talk to", "which characters are there",
                  "what characters are there", "who are you")

SETTING_PHRASES = {
    ("detail_level", "descriptive"): (
        "be more descriptive", "more detail", "more details",
        "describe everything", "descriptive mode", "full detail"),
    ("detail_level", "brief"): (
        "be brief", "less detail", "short answers", "brief mode",
        "keep it short"),
    ("detail_level", "standard"): (
        "normal detail", "standard detail", "medium detail"),
    ("swearing", "off"): ("stop swearing", "no swearing", "no cursing",
                          "clean language", "watch your language"),
    ("swearing", "mild"): ("you can swear a little", "swear a little",
                           "mild swearing"),
    ("swearing", "full"): ("swear all you want", "swear freely",
                           "full swearing", "you can swear"),
    ("humor", 0): ("no jokes", "be serious", "all business"),
    ("humor", 3): ("be funnier", "more jokes", "more humor"),
    ("humor", None): ("normal humor", "normal jokes"),
    ("earcons", False): ("no more sounds", "turn off the sounds",
                         "sounds off", "stop the sounds"),
    ("earcons", True): ("turn on the sounds", "sounds on",
                        "bring back the sounds"),
    ("narrate_actions", True): ("narrate what you do", "tell me what you're doing",
                                "narrate actions"),
    ("narrate_actions", False): ("stop narrating", "don't narrate",
                                 "just give me results"),
    ("screen_reader", "voiceover"): ("i'm using voiceover", "i am using voiceover"),
    ("screen_reader", "nvda"): ("i'm using nvda", "i am using nvda"),
    ("screen_reader", "jaws"): ("i'm using jaws", "i am using jaws"),
    ("screen_reader", "talkback"): ("i'm using talkback", "i am using talkback"),
}
SETTINGS_REPORT_PHRASES = ("what are my settings", "read my settings",
                           "settings report", "my settings")

SETTING_SAY = {
    "detail_level": {"descriptive": "Full detail from now on.",
                     "brief": "Brief from now on.",
                     "standard": "Standard detail from now on."},
    "swearing": {"off": "No more swearing.", "mild": "A little swearing, then.",
                 "full": "Swearing unlocked."},
    "humor": {0: "All business.", 3: "Turning the humor up.",
              None: "Humor back to my normal."},
    "earcons": {False: "Sounds off. I'll say on it instead.",
                True: "Sounds back on."},
    "narrate_actions": {True: "I'll narrate each step.",
                        False: "Results only from now on."},
    "screen_reader": {"voiceover": "Got it, VoiceOver.", "nvda": "Got it, NVDA.",
                      "jaws": "Got it, JAWS.", "talkback": "Got it, TalkBack."},
}


def match_setting(text: str):
    """(key, value) for a settings phrase, "report" for a settings
    report, "roster" for the character list, or None."""
    if not ENABLED:
        return None
    n = _norm(text).replace("’", "'")
    if n in ROSTER_PHRASES:
        return "roster"
    if n in SETTINGS_REPORT_PHRASES:
        return "report"
    for kv, phrases in SETTING_PHRASES.items():
        if n in phrases:
            return kv
    return None


def settings_report() -> str:
    hum = effective("humor")
    return (f"{active().get('name')} is on. Detail is "
            f"{effective('detail_level')}. Swearing is {effective('swearing')}. "
            f"Humor is {hum} out of 3. Sounds are "
            f"{'on' if effective('earcons') else 'off'}. Screen reader is "
            f"{effective('screen_reader')}. I call you "
            f"{effective('call_me') or 'nothing in particular'}.")


def set_profile(key, value, write_config_key) -> bool:
    """Update one profile key in memory and on disk; True if saved."""
    prof = dict(CFG.get("profile") or {})
    prof[key] = value
    return write_config_key("profile", prof)
