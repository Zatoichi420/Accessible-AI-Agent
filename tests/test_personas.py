"""Characters and settings: run with `python tests/test_personas.py` (no
pytest needed). Exits non-zero on the first failure."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backtalk import personas as p  # noqa: E402
from backtalk.config import CFG  # noqa: E402

CFG["profile"] = {}       # test against the shipped defaults

CASES = [
    # the registry loads, Data is the default
    (p.ENABLED, True),
    (p.active_id(), "data"),
    (p.greeting(), "Captain on the bridge. All systems are nominal and "
                   "awaiting your commands."),
    (p.effective("detail_level"), "descriptive"),
    (p.effective("call_me"), "Captain"),
    # switch phrases, including speech-recognition slips
    (p.match_switch("Switch to Friday."), "friday"),
    (p.match_switch("switch over to Mister Data please"), "data"),
    (p.match_switch("Edith, take over"), "edith"),
    (p.match_switch("switch to edit"), "edith"),
    (p.match_switch("put Jarvis on"), "jarvis"),
    (p.match_switch("let me talk to Ultron"), "ultron"),
    (p.match_switch("bring up Spock"), "spock"),
    # not switches
    (p.match_switch("switch to the deep model"), None),
    (p.match_switch("switch to dark mode in Xcode"), None),
    (p.match_switch("what's the data in this file"), None),
    # settings phrases
    (p.match_setting("Be more descriptive."), ("detail_level", "descriptive")),
    (p.match_setting("stop swearing"), ("swearing", "off")),
    (p.match_setting("No more sounds!"), ("earcons", False)),
    (p.match_setting("I'm using NVDA"), ("screen_reader", "nvda")),
    (p.match_setting("who can I talk to"), "roster"),
    (p.match_setting("what are my settings"), "report"),
    (p.match_setting("be more careful with that file"), None),
    # the prompt carries the core rules, the character and the settings
    ("Never condescending" in p.build_prompt(), True),
    ("Lieutenant Commander Data" in p.build_prompt(), True),
    ("VoiceOver" in p.build_prompt(), True),
    ("Do not swear." in p.build_prompt(), True),
]

# a profile setting overrides the character default
CFG["profile"] = {"character": "spock", "swearing": "off"}
CASES += [
    (p.active_id(), "spock"),
    (p.effective("swearing"), "off"),
    (p.effective("detail_level"), "standard"),
]
p.apply_voice()
CASES += [
    (CFG["_el_voice"], p.REGISTRY["spock"]["elevenlabs_voice_id"]),
    (CFG["_kokoro_voice"], "am_michael"),
]
# a character with no ElevenLabs voice yet speaks with the built-in one
CFG["profile"] = {"character": "friday"}
p.apply_voice()
CASES += [(CFG["_el_voice"], ""), (CFG["_kokoro_voice"], "bf_emma")]
# {user_name} fills in, or drops out cleanly when unset
CFG["profile"] = {"character": "ultron"}
CASES += [(p.greeting(), "Shall we make something that outlives us?"),
          (p.effective("call_me"), "")]
CFG["profile"] = {"character": "ultron", "user_name": "Alex",
                  "about_me": "Builds accessible games."}
CASES += [(p.greeting(), "Alex. Shall we make something that outlives us?"),
          (p.effective("call_me"), "Alex"),
          ("ABOUT THE USER: Name: Alex. Builds accessible games."
           in p.build_prompt(), True)]
# an unknown character falls back instead of crashing
CFG["profile"] = {"character": "hal"}
CASES += [(p.active_id() in p.REGISTRY, True)]

for i, (got, want) in enumerate(CASES):
    if got != want:
        print(f"FAIL case {i}: got {got!r}, want {want!r}")
        sys.exit(1)
print(f"all {len(CASES)} persona checks passed")
