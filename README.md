# Accessible AI Agent

A talking AI assistant built for blind and low-vision computer users. You
hold a key, talk, and it answers out loud. It can describe your screen, web
pages and images in as much detail as you want, identify things you hold
up to your computer's camera, work with files and apps, and remember
things. It is designed to be encouraging and never
condescending.

It comes with six characters you can switch between by voice:

- **Data** (the default): precise, kind, curious, very descriptive.
- **Jarvis**: a calm British butler with dry wit.
- **Friday**: quick, warm, short answers.
- **Edith**: careful and security-minded, good for email and money.
- **Ultron**: theatrical and blunt about ideas, never about you.
- **Spock**: logical and deadpan.

Say "switch to Friday" and Friday takes over, remembering everything Data
knew a second earlier.

> **This is an early test version.** It has been built and tested by one
> blind user on one Mac. Please report anything that doesn't work, and
> especially anything that is hard to use with a screen reader. See
> "Feedback" below.

## What you need

- A Mac with macOS 14 or newer (Apple Silicon is fastest), or a Windows
  10 or 11 PC. The Windows version is less tested so far.
- A paid Claude subscription (Pro is enough). The assistant runs on Claude
  Code, which uses your subscription. There is nothing else to pay for.
- About 2 GB of free disk space for the speech models.
- A microphone (the built-in one works) and speakers or headphones.
- For the camera features, a webcam (the built-in one works).
- Optional: an ElevenLabs account for more natural voices. Without it, the
  free built-in voices are used.

## Install

Everything below is done by keyboard. On a Mac, use Terminal: press
Command+Space, type Terminal, press Return. On Windows, use PowerShell:
press the Windows key, type PowerShell, press Return.

1. Install Claude Code, if you don't have it. Paste this line into Terminal
   and press Return:

   On a Mac:

   ```
   curl -fsSL https://claude.ai/install.sh | bash
   ```

   On Windows (PowerShell):

   ```
   irm https://claude.ai/install.ps1 | iex
   ```

   Windows also needs Git: `winget install --id Git.Git -e`, then close
   and reopen PowerShell.

   Then type `claude` and press Return, and follow the sign-in steps. When
   you are signed in, type `/exit` and press Return.

2. Download this assistant. Paste these two lines, pressing Return after
   each:

   ```
   git clone https://github.com/Zatoichi420/Accessible-AI-Agent.git ~/accessible-agent
   cd ~/accessible-agent
   ```

   On Windows, the same two lines work in PowerShell. If macOS asks to
   install the command line developer tools, press Return to accept, wait
   for it to finish, then run the two lines again.

3. Start the setup assistant. Type `claude` and press Return, then type:

   ```
   read SETUP.md and set me up
   ```

   Claude installs everything, asks you a few questions one at a time (your
   name, your screen reader, which character you want, which key to hold to
   talk), and tests the voice with you. Answer in plain words. It takes
   about 10 to 15 minutes, mostly downloading.

## Using it

- **Talk:** hold the talk key (the setup picks one that doesn't clash with
  your screen reader, usually Right Option), speak, let go.
- **Interrupt:** press the talk key while it is speaking.
- **Type instead:** type in the Terminal window and press Return.
- **Hang up:** say "goodbye Data" (or whichever character is on).

### Things you can say

| Say | What happens |
|---|---|
| "switch to Jarvis" (or any character) | That character takes over |
| "who can I talk to" | Lists the characters |
| "be more descriptive" / "be brief" / "normal detail" | How much detail you get |
| "stop swearing" / "you can swear" | Swearing off or on |
| "no jokes" / "be funnier" | Humor level |
| "no more sounds" / "turn on the sounds" | The listening and thinking tones |
| "I'm using NVDA" (or VoiceOver, JAWS, TalkBack) | Instructions match your screen reader |
| "what are my settings" | Reads your settings |
| "repeat that" / "talk slower" / "talk faster" | Replay or change pace |

All settings are saved, so they stick after a restart.

### The camera ("what am I holding?")

**The camera is off unless you choose to turn it on.** Camera use is
voluntary. Say "turn on the camera": the assistant explains what it does,
then waits for you to say "confirm". Say "turn off the camera" any time.
The person who made this assistant has no access to your camera, photos
or recordings; see `PRIVACY.md`.

Once you turn it on, it works like Alexa's Show and Tell on the Echo Show:
hold an item about a foot from your computer's camera and ask. It tells you
what it is (brand, product, size, best-by date if it can read it). If it
can't see well, it tells you how to move the item, for example "turn it
around to show the label", and you ask again.

| Say | What it does |
|---|---|
| "turn on the camera" / "turn off the camera" | Your choice, any time |
| "what am I holding" / "what's in my hand" / "what is this" | Identifies the item |
| "read this" / "read the label" / "what does this say" | Reads the text |
| "what color is this" | Names the colors |
| "describe what you see" / "what's in front of me" | Describes the scene |
| "delete my photos" | Deletes the saved photo |

A photo is taken only when you ask, and only the most recent one is kept
on your computer. Each photo you ask about is sent to Claude, under your
own Claude account, to be described.

The first time you use it, your computer asks for camera permission. On a
Mac, allow Terminal (System Settings, Privacy and Security, Camera). On
Windows, turn on "Let desktop apps access your camera" (Settings, Privacy
and security, Camera).

## Your privacy

Everything runs on your computer, under your own accounts. The person who
made this assistant runs no server, collects nothing, and has no access to
your camera, microphone, photos, recordings, transcripts or files. Your
voice is turned into text on your computer. What you say, as text, goes to
Claude under your own account so it can answer. Full details, including
what is saved and how to delete it: `PRIVACY.md`.

## Safety

- It asks out loud before doing anything that changes things (editing
  files, sending email). Risky actions need an exact phrase, like "confirm
  send".
- It **never** types into password, PIN or security-code fields. When it
  reaches one, it stops and tells you the field is ready for you.
- It never enters card numbers, bank details or Social Security numbers,
  and never agrees to a payment.
- Passwords, keys and card numbers are blanked out of what it says and of
  the saved transcripts.

## Feedback

Please open an issue on this repository (the Issues tab on GitHub) and say
what you tried, what happened, and which screen reader you use. If GitHub's
issue form is hard to use, ask the assistant itself: say "help me write a
bug report for the accessible agent", and it will draft one with you.

## Credits and license

Built on [backtalk](https://github.com/jaredrhod/backtalk) by Jared
Rhodenizer, which provides the voice loop. Licensed under the GNU Affero
General Public License version 3 (see `LICENSE`). The characters are
inspired by fictional characters from Marvel and Star Trek; this project is
not affiliated with or endorsed by their owners, and all voices are
original, not imitations of any actor.

The original backtalk README is in `BACKTALK-README.md`.
