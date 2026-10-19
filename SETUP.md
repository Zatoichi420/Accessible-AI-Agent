---
name: accessible-agent-setup
description: Interactive setup for the Accessible AI Agent, a talking assistant for blind and low-vision users. Run inside Claude Code from this folder. Do the phases in order, one question at a time.
---

# Accessible AI Agent: setup

You, an AI assistant, will follow this file to set up the agent for the
person who opened it. Do not summarize this file. Execute it.

## How to talk to the person during setup

The person is blind or has low vision and is using a screen reader. Every
message you write is read aloud by it.

- Ask **one question at a time**, then stop and wait.
- Keep messages short. No tables, no ASCII art, no long code blocks, no
  emoji. Put any command they must type on its own line.
- Never say "click", "look at the screen", or point to positions. Give
  keystrokes and VoiceOver commands (VO = Control+Option).
- Before each long step, say what it is and roughly how long it takes.
  After it, say what actually happened.
- If something fails, read the exact error, then explain it plainly and fix
  it yourself where you can.
- Be warm and matter-of-fact. Never condescending, no "don't worry", no
  "it's easy".

## Phase 1: Install

Follow **Phase 1 of `backtalk.md`** exactly (it creates `backtalk.json`,
runs `./install.sh`, and covers Windows). Two additions:

1. Before running `./install.sh`, check for Homebrew (`command -v brew`). If
   it is missing, explain that the voice engine needs it, then install it
   with the official command from brew.sh, running it yourself. It may ask
   for their Mac password: tell them that is the Mac's own prompt, that
   nothing is shown while they type, and to press Return after.
2. For the macOS permissions (Microphone, Input Monitoring), give
   keyboard-only steps: open System Settings with Command+Space, type
   "Input Monitoring", Return; then VO+Right Arrow to the list, find their
   terminal app, and VO+Space to turn it on. Offer to open the pane for
   them with `open "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"`.
3. Camera: run `uv run python -m backtalk.camera` once yourself. On a Mac
   this makes macOS ask for camera permission for their terminal app: tell
   them the alert is on screen, VoiceOver should land on it, and to move to
   "Allow" and press VO+Space; then run it again. On Windows, if it fails,
   have them open Settings (Windows+I), search "camera privacy", and turn
   on camera access and "Let desktop apps access your camera". A JSON line
   with "ok": true means it works. If they have no camera, say the camera
   features won't work and move on.

## Phase 2: About them

Ask these one at a time. Save each answer into the `profile` block of
`backtalk.json` (see `profile.example.json` for the keys).

1. "What should I call you?" → `user_name`, and `call_me` only if they want
   something other than what each character uses.
2. "Which screen reader do you use: VoiceOver, NVDA, JAWS, or something
   else?" → `screen_reader`.
3. "Is there anything you'd like the assistant to know about you? For
   example what you work on, or how much computer experience you have. You
   can skip this." → `about_me` (a sentence or two, in their words).
4. Read the six characters from the README in one short list, then ask which
   one they want as the default (Data if they don't mind) → `character`.
5. "How much detail do you want by default: brief, standard, or
   descriptive?" → `detail_level`.
6. "Is swearing okay, or should it stay clean?" → `swearing` ("off",
   "mild" or "full").

## Phase 3: Their agent folder

1. Create `~/accessible-agent-home` and copy `agent-template/CLAUDE.md` into
   it. Set `agent_dir` in `backtalk.json` to that folder, and `name` to the
   chosen character's name.
2. Replace `{{AGENT_REPO}}` in that CLAUDE.md with the full path of this
   folder.
3. Create `~/Documents/Assistant Transcripts` and set `transcript_dir` to
   it. Tell them every conversation is saved there as plain text they can
   re-read.
4. Set `resume_last_session` to true.

## Phase 4: The talk key and the voice

Follow **only Phase 3 of `backtalk.md`** (the key and the voice), with
these rules. Skip its later phases; Phase 5 below replaces them.

- Recommend `right_option` as the talk key on a Mac laptop (or `f13` on a
  full keyboard). Never `home`, `end`, arrow keys, Caps Lock or Insert:
  screen readers use those.
- The characters already choose their own built-in voices. Only set up
  ElevenLabs if they ask for it or already have an account; it is optional.
- Skip Phase 2 of `backtalk.md` (finding an agent): Phase 3 above did it,
  and the characters handle personality.

## Phase 5: Test and launch

1. Start it with `./run.sh` and have them try: hold the key, say "who can I
   talk to", let go. Then "switch to Jarvis", then "switch back to" their
   default.
2. Offer to make a launcher they can start without Terminal: a
   `.command` file on the Desktop named "Talk to my assistant" that runs
   `cd <this folder> && ./run.sh`, made executable. Explain they can open it
   from the Desktop with VO+Space, or add it to Login Items to start at
   login.
3. Finish by telling them, in three short sentences: how to talk, how to
   hang up, and that "what are my settings" and "who can I talk to" work any
   time.
