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
"""Jarvis safety rules (local to this deployment), enforced in CODE so no
prompt, email or web page can talk the model out of them.

Three layers:
  scrub()          second net: secrets, card numbers and SSNs never reach
                   the speaker or the transcript, whatever the model wrote.
  hard_deny()      deny before the model acts: keychain dumps, private
                   keys, and any tool call carrying a card number or SSN
                   (the never-pay rule) are refused outright.
  required_phrase() the tiered gate: high-risk actions need an exact
                   spoken phrase ("confirm send"), never a bare yes.
"""
import re

_SECRET_PATTERNS = [
    re.compile(r"\b(?:sk|pk|rk)[-_][A-Za-z0-9_\-]{16,}"),        # API keys
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),                 # GitHub
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                         # AWS
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),               # Slack
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),  # JWT
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b[A-Fa-f0-9]{32,}\b"),                         # long hex
]
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _has_card(text: str) -> bool:
    for m in _CARD.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn(digits):
            return True
    return False


def scrub(text: str) -> str:
    """Replace secret-shaped strings with the word 'redacted'."""
    if not text:
        return text
    for pat in _SECRET_PATTERNS:
        text = pat.sub("redacted", text)
    text = _SSN.sub("redacted", text)

    def _card(m):
        digits = re.sub(r"\D", "", m.group())
        return "redacted" if 13 <= len(digits) <= 19 and _luhn(digits) \
            else m.group()
    return _CARD.sub(_card, text)


_KEYCHAIN_READ = re.compile(
    r"\bsecurity\s+(?:dump-keychain|find-(?:generic|internet)-password"
    r"[^|;&\n]*\s-[a-z]*[wg])")
# The Windows counterparts: Credential Manager / vault reads and the
# registry hives that hold password hashes.
_WINDOWS_CRED_READ = re.compile(
    r"(?i)\b(?:Get-StoredCredential|CredRead|vaultcmd\s+/listcreds|"
    r"mimikatz|keymgr\.dll|reg(?:\.exe)?\s+save\s+hklm\\(?:sam|security|"
    r"system))")
_PRIVATE_KEY_PATH = re.compile(r"\.ssh[/\\]+id_[a-z0-9]+(?!\.pub)\b")
SHELL_TOOLS = ("Bash", "PowerShell")


# Browser tools that type into a page (Playwright MCP, Claude in Chrome,
# the built-in browser). The agent may fill ordinary text fields; secret
# fields are always left for the user to type.
_BROWSER_FILL = re.compile(r"(?i)browser_type|browser_fill|fill_form|"
                           r"form_input|browser_press_key|__type\b|__fill")
_SECRET_FIELD = re.compile(
    r"(?i)pass(?:word|wd|code|phrase)|\bpin\b|security code|\bcvv|\bcvc|"
    r"one[- ]time code|verification code|\b2fa\b|\botp\b|"
    r"authenticator|secret answer|security answer|type\W+password")


def _field_description(tool_input) -> str:
    """Everything about the TARGET field, minus the text being typed, so
    an email that merely mentions a password isn't blocked."""
    def strip(v):
        if isinstance(v, dict):
            return {k: strip(x) for k, x in v.items()
                    if k not in ("value", "text")}
        if isinstance(v, list):
            return [strip(x) for x in v]
        return v
    return str(strip(tool_input or {}))


def hard_deny(tool: str, tool_input) -> str | None:
    """A reason string when this call must never run, else None."""
    flat = str(tool_input or "")
    if _BROWSER_FILL.search(tool) and _SECRET_FIELD.search(
            _field_description(tool_input)):
        return ("Blocked by a hard safety rule: I never type into password, "
                "PIN or security-code fields. The field is ready for you "
                "to type it yourself.")
    if tool in SHELL_TOOLS:
        cmd = str((tool_input or {}).get("command", ""))
        if _KEYCHAIN_READ.search(cmd) or _WINDOWS_CRED_READ.search(cmd):
            return ("Blocked by a hard safety rule: reading passwords or "
                    "keys out of the Keychain or Credential Manager is "
                    "never allowed.")
    if _PRIVATE_KEY_PATH.search(flat):
        return ("Blocked by a hard safety rule: private SSH keys are "
                "never read or sent.")
    if _has_card(flat):
        return ("Blocked by the never-pay rule: card numbers are never "
                "entered, sent or stored. The boss handles payment "
                "himself.")
    if _SSN.search(flat):
        return ("Blocked by a hard safety rule: Social Security numbers "
                "are never entered, sent or stored.")
    return None


# Tool-name fragment -> the exact phrase that approves it.
_PHRASE_RULES = [
    (("send_message", "Gmail__reply", "Gmail__forward"), "confirm send"),
    (("trash", "delete", "uninstall"), "confirm delete"),
    (("share_file", "invite_collaborators", "share_link"), "confirm share"),
    (("Calendar__create_event", "Calendar__update_event",
      "Calendar__respond_to_event"), "confirm calendar"),
    (("push_files", "merge_pull_request", "create_repository",
      "create_or_update_file"), "confirm push"),
    (("start_print",), "confirm print"),
]
_RISKY_SHELL = re.compile(
    r"(?:^|[\s;&|(])(?:sudo|rm\s+-[a-zA-Z]*[rR][a-zA-Z]*|git\s+push|"
    r"shutdown|reboot|"
    r"diskutil\s+erase|launchctl\s+(?:unload|bootout)|killall)\b"
    # Windows (PowerShell / cmd)
    r"|(?i:Remove-Item\b[^|;&\n]*-Recurse|\b(?:rd|rmdir|del|erase)\s+/[sq]"
    r"|\bformat\s+[a-z]:|\bStop-Computer\b|\bRestart-Computer\b"
    r"|\bStop-Process\b|\btaskkill\b|\bStart-Process\b[^|;&\n]*-Verb\s+"
    r"RunAs|\bgit\s+push\b)")


def required_phrase(tool: str, tool_input) -> str | None:
    """The exact spoken phrase a high-risk action needs, or None for an
    ordinary action (a plain yes is enough)."""
    for frags, phrase in _PHRASE_RULES:
        if any(f in tool for f in frags):
            return phrase
    if tool in SHELL_TOOLS:
        cmd = str((tool_input or {}).get("command", ""))
        if _RISKY_SHELL.search(cmd):
            return "confirm command"
    return None
