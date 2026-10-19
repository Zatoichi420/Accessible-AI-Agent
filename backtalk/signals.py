# backtalk: talk to your Claude Code agent out loud.
# Copyright (C) 2026 Jared Rhodenizer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The signal bus — tiny files any other program can watch.

The voice line leaves notes; faces read the notes. That one dumb trick
is the whole integration surface:

  .voice_state        idle | listening | thinking | speaking
  .voice_waveform     JSON {ts, samples: [64 floats]} while audio plays
  .voice_loading_pid  exists while the thinking sound is playing

Written to signals_dir (default: the repo root). Visualizers built on
this contract just work.

THE BAREHANDS SEAM: set barehands_state_dir in backtalk.json to a
barehands checkout's state/ folder and the same signals are mirrored in
its format (state/state as a bare word, state/wave.json normalized
0..1) — the on-screen ring becomes your agent's face with zero glue.

Every write is wrapped: the bus must never crash the voice line.
"""
import json
import os
import subprocess
import sys
import time

import numpy as np

from backtalk.config import CFG

if sys.platform == "win32":
    import winsound
else:
    winsound = None

_DIR = CFG["signals_dir"]
_STATE_FILE = os.path.join(_DIR, ".voice_state")
_WAVEFORM_FILE = os.path.join(_DIR, ".voice_waveform")
_LOADING_PID_FILE = os.path.join(_DIR, ".voice_loading_pid")
_DIRECTION_FILE = os.path.join(_DIR, ".voice_direction")
_REPLY_DONE_FILE = os.path.join(_DIR, ".voice_reply_done")

_BH = CFG.get("barehands_state_dir") or ""
_BH_STATE = os.path.join(_BH, "state") if _BH else ""
_BH_WAVE = os.path.join(_BH, "wave.json") if _BH else ""

_THINKING_SOUND = CFG.get("thinking_sound") or ""
_LISTENING_SOUND = CFG.get("listening_sound") or ""
# Earcons on/off, flipped live by the voice console ("no more sounds").
EARCONS = {"on": bool((CFG.get("profile") or {}).get("earcons", True))}

_WAVEFORM_MIN_INTERVAL = 1.0 / 15   # ~15 writes/sec is plenty for 60fps reads
_last_waveform_write = 0.0
_static_proc: subprocess.Popen | None = None


def set_state(name: str):
    """Write the state. Never raises — the show must go on."""
    try:
        with open(_STATE_FILE, "w") as f:
            f.write(name)
    except OSError:
        pass
    if _BH_STATE:
        try:
            with open(_BH_STATE, "w") as f:
                f.write(name)
        except OSError:
            pass


def feed_waveform(pcm: np.ndarray):
    """Feed one PCM block (int16) — throttled, downsampled to 64 points.

    Also re-asserts state="speaking" on the same throttle: this only runs
    while the mouth is audibly playing, so the bus self-heals within
    ~70ms if a stray writer stomps the state mid-speech. (That self-heal
    rule once closed a bug that took a whole evening to find.)"""
    global _last_waveform_write
    if pcm.size == 0:
        return
    now = time.time()
    if now - _last_waveform_write < _WAVEFORM_MIN_INTERVAL:
        return
    _last_waveform_write = now
    try:
        idx = np.linspace(0, pcm.size - 1, 64).astype(int)
        raw = pcm[idx].astype(float)
        with open(_WAVEFORM_FILE, "w") as f:
            f.write(json.dumps({"ts": now, "samples": raw.tolist()}))
        if _BH_WAVE:
            norm = np.clip(np.abs(raw) / 32768.0, 0.0, 1.0)
            with open(_BH_WAVE, "w") as f:
                f.write(json.dumps({"ts": now, "samples": norm.tolist()}))
    except (OSError, ValueError):
        pass
    set_state("speaking")


def direction(items):
    """Stage directions the agent wrote into its reply, published at the
    moment the audio carrying them starts playing.

    Your agent can emit `<<anything>>` inline and backtalk will never speak
    it. What the tag MEANS is deliberately not backtalk's business: it
    publishes the raw strings and something else decides. That is the whole
    reason this is a file and not a plugin API.

    The timing is the point, and it is the one part a watcher cannot do for
    itself: these fire when the sentence becomes AUDIBLE, not when the model
    generated it. A screen cue lands on the spoken word instead of seconds
    early. Never raises."""
    if not items:
        return
    try:
        with open(_DIRECTION_FILE, "w") as f:
            f.write(json.dumps({"ts": time.time(), "directions": list(items)}))
    except OSError:
        pass


def reply_done():
    """One reply has finished speaking and its audio has fully drained.

    Distinct from the state going idle, which also happens in the gaps
    BETWEEN sentences of the same reply. Anything waiting for the agent to
    genuinely stop talking wants this rather than a state flicker. Never
    raises."""
    try:
        with open(_REPLY_DONE_FILE, "w") as f:
            f.write(json.dumps({"ts": time.time()}))
    except OSError:
        pass


def _player_cmd(path: str) -> list[str] | None:
    """Subprocess-based player, for platforms with no fast in-process
    option. Windows deliberately isn't handled here — see static_start,
    static_stop, and cue_listening, which call winsound directly instead.
    An earlier version of this routed Windows through here too (spawning
    a whole python.exe subprocess just to call winsound), which added
    enough startup latency that cue_listening's chirp could land after
    the moment it was meant to mark, sometimes late enough to go
    unnoticed entirely — a one-shot cue fired at a key press has to be
    near-instant, and a subprocess spawn wasn't."""
    if sys.platform == "darwin":
        return ["afplay", "-v", "0.35", path]
    if sys.platform == "win32":
        return None
    for cand in ("ffplay", "aplay", "paplay"):
        from shutil import which
        if which(cand):
            if cand == "ffplay":
                return ["ffplay", "-nodisp", "-autoexit", "-loglevel",
                        "quiet", "-volume", "35", path]
            return [cand, path]
    return None


def static_start():
    """Optional thinking sound — plays while the brain works."""
    global _static_proc
    if not EARCONS["on"] or not _THINKING_SOUND \
            or not os.path.exists(_THINKING_SOUND):
        return
    static_stop()
    if winsound is not None:
        # winsound plays exactly one sound at a time per process, and a
        # new PlaySound call auto-stops whatever's already playing — so
        # SND_LOOP + SND_ASYNC here is both the loop and its own
        # guaranteed-clean handoff from any prior sound.
        try:
            winsound.PlaySound(
                _THINKING_SOUND,
                winsound.SND_FILENAME | winsound.SND_ASYNC
                | winsound.SND_LOOP | winsound.SND_NODEFAULT)
            with open(_LOADING_PID_FILE, "w") as f:
                f.write("winsound")  # no real PID to give; marks "is playing"
        except OSError:
            pass
        return
    cmd = _player_cmd(_THINKING_SOUND)
    if not cmd:
        return
    try:
        _static_proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(_LOADING_PID_FILE, "w") as f:
            f.write(str(_static_proc.pid))
    except OSError:
        _static_proc = None


def static_stop():
    global _static_proc
    if winsound is not None:
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except OSError:
            pass
    elif _static_proc is not None:
        try:
            _static_proc.terminate()
        except OSError:
            pass
        _static_proc = None
    try:
        os.remove(_LOADING_PID_FILE)
    except OSError:
        pass


def cue_listening():
    """One-shot earcon fired the instant the mic opens (key down).

    Of the four states (idle/listening/thinking/speaking), "listening"
    was the only one with no audio cue of its own — thinking has its
    loop, speaking has the reply itself, but a screen-reader user knew
    the mic was live only by the physical feel of holding the key down.
    Deliberately separate from static_start()/static_stop(): those track
    a long-lived PID for early cancellation, this is fire-and-forget —
    by the time anyone could react, a short chirp is already over.
    Never raises."""
    if not EARCONS["on"] or not _LISTENING_SOUND \
            or not os.path.exists(_LISTENING_SOUND):
        return
    if winsound is not None:
        try:
            winsound.PlaySound(
                _LISTENING_SOUND,
                winsound.SND_FILENAME | winsound.SND_ASYNC
                | winsound.SND_NODEFAULT)
        except OSError:
            pass
        return
    cmd = _player_cmd(_LISTENING_SOUND)
    if not cmd:
        return
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except OSError:
        pass
