"""Camera checks that need no real camera: run with
`python tests/test_camera.py`. Exits non-zero on the first failure."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np  # noqa: E402

from backtalk import camera as c  # noqa: E402
from backtalk import safety  # noqa: E402
from backtalk.config import CFG, DEFAULTS  # noqa: E402

# Off by default: no photo, the standalone command refuses, and only the
# user's spoken opt-in can turn it on.
CFG["camera"] = DEFAULTS["camera"]
off_shot = c.capture(index=0, settle=0.1)
OFF_CASES = [
    (DEFAULTS["camera"], False),
    (c.enabled(), False),
    (off_shot["ok"], False),
    (off_shot["error"], c.OFF_MESSAGE),
    ("no access to your camera" in c.DISCLAIMER, True),
    (c.match_control("Turn on the camera."), "camera_on"),
    (c.match_control("turn off the camera"), "camera_off"),
    (c.match_control("delete my photos"), "camera_delete"),
    (c.match_control("turn on the lights"), None),
    # the agent can't switch it on by editing the config
    (bool(safety.hard_deny("Edit", {"file_path": "backtalk.json",
                                    "old_string": '"camera": false',
                                    "new_string": '"camera": true'})), True),
    (bool(safety.hard_deny("Bash", {"command":
        "python3 -c \"d['camera']=True\""})), True),
    (bool(safety.hard_deny("Bash", {"command":
        "jq '.camera = true' backtalk.json"})), True),
    (bool(safety.hard_deny("Edit", {"file_path": "backtalk.json",
                                    "new_string": '"camera": false'})), False),
]
CFG["camera"] = True       # the rest checks behavior once the user opted in

rng = np.random.default_rng(0)
sharp = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)   # busy detail
dark = np.full((480, 640, 3), 10, dtype=np.uint8)
bright = np.full((480, 640, 3), 250, dtype=np.uint8)
blurry = np.full((480, 640, 3), 128, dtype=np.uint8)           # no edges

shot = {"ok": True, "path": "/tmp/photo.jpg", "issues": ["it is dark"]}
missing = c.capture(index=97, settle=0.2)

CASES = OFF_CASES + [
    (c.match("What am I holding?"), "identify"),
    (c.match("what's in my hand"), "identify"),
    (c.match("Read the label."), "read"),
    (c.match("describe what you see"), "scene"),
    (c.match("What colour is this?"), "color"),
    (c.match("what am I holding on to in this plan"), None),
    (c.quality_issues(sharp), []),
    (any("dark" in i for i in c.quality_issues(dark)), True),
    (any("washed out" in i for i in c.quality_issues(bright)), True),
    (any("blurry" in i for i in c.quality_issues(blurry)), True),
    ("/tmp/photo.jpg" in c.prompt_for("identify", shot), True),
    ("it is dark" in c.prompt_for("identify", shot), True),
    # no camera at that index: a spoken reason, never a crash
    (missing["ok"], False),
    (len(missing["error"]) > 20, True),
]

for i, (got, want) in enumerate(CASES):
    if got != want:
        print(f"FAIL case {i}: got {got!r}, want {want!r}")
        sys.exit(1)
print(f"all {len(CASES)} camera checks passed")
