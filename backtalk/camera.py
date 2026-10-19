# Camera additions to backtalk ("what am I holding?").
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Take a photo with the computer's camera and have the agent describe it.

Modeled on Alexa's Show and Tell on the Echo Show: hold an item about a
foot from the camera, ask "what am I holding?", get a short answer, and if
the view isn't good enough, get told how to move the item (closer, turn it
to the label, more light) and ask again.

OFF BY DEFAULT. Camera use is voluntary: only the user can turn it on, by
saying "turn on the camera" and then "confirm" after hearing what it does.
The agent can't turn it on (safety.py blocks config edits that would), and
the standalone command refuses while it is off. A photo is taken only when
the user asks; only the most recent one is kept on disk; "delete my
photos" or turning the camera off removes them.

Works on macOS (AVFoundation) and Windows (DirectShow) through OpenCV.
Also runnable on its own, so typed and phone sessions can take a photo:

    python -m backtalk.camera            # prints JSON: ok, path, issues
"""
import json
import sys
import time
from pathlib import Path

from backtalk.config import CFG, REPO

PHOTO_DIR = REPO / "state" / "camera"

# Spoken when the user asks to turn the camera on, before they confirm.
DISCLAIMER = (
    "Before you decide: using the camera is completely your choice. When "
    "it's on, I take a photo only when you ask, like what am I holding. "
    "The photo stays on this computer, and it is sent to Claude, under "
    "your own Claude account, to be described. The person who made this "
    "assistant has no access to your camera, your photos or your "
    "recordings. I keep only the latest photo, and you can say delete my "
    "photos or turn off the camera any time. Say confirm to turn the "
    "camera on.")
OFF_MESSAGE = ("The camera is off. It only comes on if you choose to turn "
               "it on: say turn on the camera, and I'll explain what it "
               "does first.")
CONTROL = {
    "camera_on": ("turn on the camera", "enable the camera", "camera on",
                  "turn the camera on", "switch on the camera"),
    "camera_off": ("turn off the camera", "disable the camera", "camera off",
                   "turn the camera off", "switch off the camera"),
    "camera_delete": ("delete my photos", "delete the photos",
                      "delete my pictures", "delete the pictures",
                      "erase my photos"),
}


def enabled() -> bool:
    return CFG.get("camera") is True


def match_control(text: str):
    """"camera_on" / "camera_off" / "camera_delete", or None."""
    n = " ".join(text.lower().replace(",", " ").split()).strip(" .!?")
    for verb, phrases in CONTROL.items():
        if n in phrases:
            return verb
    return None


def delete_photos() -> int:
    """Remove every saved photo. Returns how many were deleted."""
    n = 0
    for f in PHOTO_DIR.glob("photo-*.jpg"):
        try:
            f.unlink()
            n += 1
        except OSError:
            pass
    return n

# What the user says -> what the agent is asked to do with the photo.
TASKS = {
    "identify": (
        "Identify the item the user is holding up to the camera. Lead with "
        "what it is: brand, product, and variety, flavor or size if "
        "visible. Then add useful details from the packaging (for food: "
        "expiry or best-by date if readable, key allergens) as the detail "
        "setting allows."),
    "read": (
        "Read all the text on the item or page in the photo, in reading "
        "order. Say first what kind of thing it is (label, letter, "
        "screen, sign), then the text. For long text, give the main points "
        "first and offer to read the rest."),
    "scene": (
        "Describe what the camera sees: the main things in view, where they "
        "are (left, right, near, far), people if any (no guesses about "
        "identity), and anything that looks important or unsafe."),
    "color": (
        "Say the main color or colors of the item the user is holding, in "
        "plain everyday names (navy blue, olive green), plus pattern if "
        "any (striped, plaid)."),
}
PHRASES = {
    "identify": ("what am i holding", "what's in my hand", "what is in my hand",
                 "what is this", "what's this", "identify this",
                 "what am i holding up", "look at this"),
    "read": ("read this", "read this to me", "read the label",
             "read this label", "what does this say", "read it"),
    "scene": ("describe what you see", "what do you see", "look around",
              "describe the room", "what's in front of me",
              "what is in front of me"),
    "color": ("what color is this", "what colour is this",
              "what color is it", "what color am i holding"),
}


def match(text: str):
    """The camera task for a spoken phrase, or None."""
    n = " ".join(text.lower().replace("’", "'").replace(",", " ")
                 .split()).strip(" .!?")
    for task, phrases in PHRASES.items():
        if n in phrases:
            return task
    return None


def _open(index: int):
    import cv2
    if sys.platform == "win32":
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    elif sys.platform == "darwin":
        backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
    else:
        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
    for be in backends:
        cap = cv2.VideoCapture(index, be)
        if cap is not None and cap.isOpened():
            return cap
        if cap is not None:
            cap.release()
    return None


def no_camera_reason() -> str:
    if sys.platform == "darwin":
        return ("I couldn't open the camera. Usually that means the app "
                "running me doesn't have camera permission. Open System "
                "Settings, Privacy and Security, Camera, and turn on "
                "Terminal (or the app you started me from), then restart me.")
    if sys.platform == "win32":
        return ("I couldn't open the camera. Check Windows Settings, Privacy "
                "and security, Camera: camera access and Let desktop apps "
                "access your camera must both be on. Also make sure no other "
                "app, like Teams or Zoom, is using the camera.")
    return "I couldn't open the camera."


def quality_issues(frame) -> list[str]:
    """Plain-language problems with a frame, for the agent and the user."""
    import cv2
    import numpy as np
    issues = []
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean = float(np.mean(gray))
    if mean < 35:
        issues.append("the picture is very dark; turn on a light or face "
                      "the light")
    elif mean > 235:
        issues.append("the picture is washed out by bright light")
    if float(cv2.Laplacian(gray, cv2.CV_64F).var()) < 25 and mean >= 35:
        issues.append("the picture is blurry; hold the item still, or move "
                      "it a little further from the camera")
    return issues


def capture(index: int | None = None, settle: float = 1.0) -> dict:
    """Take one photo. Returns {"ok", "path", "issues", "error"}."""
    if not enabled():
        return {"ok": False, "path": "", "issues": [], "error": OFF_MESSAGE}
    try:
        import cv2
    except ImportError:
        return {"ok": False, "path": "", "issues": [],
                "error": "The camera library isn't installed. Run the "
                         "update, or: uv pip install opencv-python-headless"}
    if index is None:
        index = int(CFG.get("camera_index") or 0)
    cap = _open(index)
    if cap is None:
        return {"ok": False, "path": "", "issues": [],
                "error": no_camera_reason()}
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        # Let auto-exposure and focus settle: keep reading, keep the last.
        frame, end = None, time.monotonic() + settle
        while time.monotonic() < end or frame is None:
            ok, f = cap.read()
            if ok and f is not None:
                frame = f
            elif time.monotonic() > end + 3:
                break
    finally:
        cap.release()
    if frame is None:
        return {"ok": False, "path": "", "issues": [],
                "error": "The camera opened but sent no picture. "
                         + no_camera_reason()}
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    path = PHOTO_DIR / time.strftime("photo-%Y%m%d-%H%M%S.jpg")
    cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    keep = max(1, int(CFG.get("camera_keep_photos") or 1))
    for old in sorted(PHOTO_DIR.glob("photo-*.jpg"))[:-keep]:
        try:
            old.unlink()
        except OSError:
            pass
    return {"ok": True, "path": str(path), "issues": quality_issues(frame),
            "error": ""}


def prompt_for(task: str, shot: dict) -> str:
    """What the brain is asked, once the photo exists."""
    notes = ("Camera quality notes: " + "; ".join(shot["issues"]) + "."
             if shot["issues"] else "")
    return (
        f"[The user asked the camera to look. A photo was just taken: "
        f"{shot['path']} . Open it with the Read tool.] "
        f"{TASKS[task]} {notes} "
        "Be honest about confidence: if you're not sure, say what it might "
        "be and how sure you are. If the item is cut off, too close, too "
        "far, blurry, too dark, or the label faces away, say exactly how to "
        "move it in one short sentence (for example: turn it around to show "
        "the label, move it a little closer, more to the left) and tell "
        "them to ask again. Never say the photo is unavailable unless the "
        "Read tool actually failed."
    )


def main():
    shot = capture()
    print(json.dumps(shot))
    sys.exit(0 if shot["ok"] else 1)


if __name__ == "__main__":
    main()
