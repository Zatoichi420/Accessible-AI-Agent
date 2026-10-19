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
"""Hold-to-talk — a global key listener.

HOLD the key -> mic opens. RELEASE -> mic closes and the utterance is
processed. The button IS the voice-activity detector, which is why this
mode is speaker-safe with no headphones: the mic simply isn't open while
the assistant talks, unless you press the key — and pressing while it
talks interrupts it.

THE KEY-REPEAT TRAP (the bug that kills every naive build): the OS fires
on_press events CONTINUOUSLY while a key is held. Without the held-state
filter below, every repeat reads as a fresh press and keeps cancelling
the reply before it can speak.

macOS needs Input Monitoring permission for the hosting terminal
(System Settings -> Privacy & Security -> Input Monitoring). Windows
works out of the box; some Linux desktops need the user in the `input`
group or an X11 session.
"""
import threading

from pynput import keyboard


# Friendly names -> pynput's names. pynput calls the right option key
# alt_r, not right_alt; the docs speak human, this map translates.
# (Field-caught: right_alt silently fell back to home, which Mac
# laptops cannot press, so the voice looked healthy and never fired.)
_ALIASES = {
    "right_alt": "alt_r", "left_alt": "alt_l",
    "right_option": "alt_r", "left_option": "alt_l",
    "right_ctrl": "ctrl_r", "left_ctrl": "ctrl_l",
    "right_cmd": "cmd_r", "left_cmd": "cmd_l",
    "right_shift": "shift_r", "left_shift": "shift_l",
}


def resolve_key_name(name: str) -> tuple[str, bool]:
    """Canonical pynput key name for a configured key name, and whether
    it was actually recognized (False means the caller falls back to
    'home'). Split out from resolve_key() so config.py can build a
    spoken key label — and a spoken fallback warning — that always
    matches what actually ends up listening, without needing a live
    pynput key object just to check."""
    raw = (name or "home").strip().lower()
    if len(raw) == 1:
        return raw, True
    resolved = _ALIASES.get(raw, raw)
    return (resolved, True) if hasattr(keyboard.Key, resolved) else ("home", False)


def resolve_key(name: str):
    """'home' / 'f13' / 'right_alt' / any single character -> pynput key."""
    raw = (name or "home").strip().lower()
    if len(raw) == 1:
        return keyboard.KeyCode.from_char(raw)
    resolved, ok = resolve_key_name(raw)
    if not ok:
        print(f"[ptt] unknown key {raw!r} — falling back to 'home'",
              flush=True)
        return keyboard.Key.home
    return getattr(keyboard.Key, resolved)


class PTTListener:
    def __init__(self, key="home"):
        self._key = resolve_key(key) if isinstance(key, str) else key
        self._held = False
        self._press_evt = threading.Event()
        self._listener = keyboard.Listener(on_press=self._on_press,
                                           on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def _on_press(self, k):
        if k == self._key and not self._held:   # filter key-repeat
            self._held = True
            self._press_evt.set()

    def _on_release(self, k):
        if k == self._key:
            self._held = False

    def wait_press(self):
        """Block until the key goes DOWN (one event per physical press)."""
        self._press_evt.wait()
        self._press_evt.clear()

    def is_held(self) -> bool:
        return self._held
