"""Jarvis safety rules: run with `python tests/test_safety.py` (no pytest
needed). Exits non-zero on the first failure."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backtalk import safety as s  # noqa: E402

CASES = [
    # scrubbing: secrets never reach speech or transcript
    (s.scrub("key sk-ant-api03-abcdefghijklmnopqrstuv ok"), "key redacted ok"),
    (s.scrub("card 4111 1111 1111 1111 thanks"), "card redacted thanks"),
    (s.scrub("ssn 123-45-6789"), "ssn redacted"),
    (s.scrub("call 702-555-1234 or order 1234567890"),
     "call 702-555-1234 or order 1234567890"),
    # hard denies, macOS and Windows
    (bool(s.hard_deny("Bash", {"command": "security find-generic-password -s x -w"})), True),
    (bool(s.hard_deny("PowerShell", {"command": "Get-StoredCredential -Target x"})), True),
    (bool(s.hard_deny("Bash", {"command": "reg save HKLM\\SAM sam.hiv"})), True),
    (bool(s.hard_deny("Read", {"file_path": "C:\\Users\\x\\.ssh\\id_ed25519"})), True),
    (bool(s.hard_deny("Read", {"file_path": "/Users/x/.ssh/id_ed25519.pub"})), False),
    (bool(s.hard_deny("x__form_input", {"value": "4111111111111111"})), True),
    (bool(s.hard_deny("Bash", {"command": "security list-keychains"})), False),
    (bool(s.hard_deny("Bash", {"command": "cmdkey /list"})), False),
    # browser fills: ordinary fields yes, secret fields never
    (bool(s.hard_deny("mcp__playwright__browser_type",
                      {"element": "Email address textbox", "ref": "e12",
                       "text": "name@example.com"})), False),
    (bool(s.hard_deny("mcp__playwright__browser_type",
                      {"element": "Password textbox", "ref": "e13",
                       "text": "hunter2"})), True),
    (bool(s.hard_deny("mcp__playwright__browser_fill_form",
                      {"fields": [{"name": "Name", "type": "textbox",
                                   "value": "Alex"},
                                  {"name": "PIN", "type": "textbox",
                                   "value": "1234"}]})), True),
    (bool(s.hard_deny("mcp__playwright__browser_type",
                      {"element": "Message body", "ref": "e9",
                       "text": "I forgot my password, can you reset it?"})),
     False),
    (bool(s.hard_deny("mcp__claude-in-chrome__form_input",
                      {"ref": "input[type=password]", "value": "x"})), True),
    # tiered confirm phrases
    (s.required_phrase("mcp__claude_ai_Gmail__send_message", {}), "confirm send"),
    (s.required_phrase("mcp__claude_ai_Gmail__create_draft", {}), None),
    (s.required_phrase("Bash", {"command": "rm -rf build"}), "confirm command"),
    (s.required_phrase("Bash", {"command": "rm file.txt"}), None),
    (s.required_phrase("Bash", {"command": "grep -r foo ."}), None),
    (s.required_phrase("PowerShell", {"command": "Remove-Item C:\\x -Recurse -Force"}), "confirm command"),
    (s.required_phrase("Bash", {"command": "rd /s /q build"}), "confirm command"),
    (s.required_phrase("PowerShell", {"command": "git push origin main"}), "confirm command"),
    (s.required_phrase("PowerShell", {"command": "Get-ChildItem"}), None),
    (s.required_phrase("mcp__rea__procedure_pseudo_code", {}), None),
]

failed = 0
for i, (got, want) in enumerate(CASES):
    if got != want:
        failed += 1
        print(f"FAIL case {i}: got {got!r}, want {want!r}")
print(f"{len(CASES) - failed}/{len(CASES)} safety cases passed")
sys.exit(1 if failed else 0)
