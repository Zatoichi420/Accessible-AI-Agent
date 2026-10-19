# Your data stays in your control

This assistant runs on your own computer, under your own accounts. The
person who made it runs no server, collects nothing, and has **no access**
to your camera, your microphone, your photos, your recordings, your
transcripts, your files or your settings. There is no tracking, analytics
or "phone home" of any kind in this project's code.

## The camera is off unless you turn it on

- Using the camera is **voluntary**. It is **off** when you install the
  assistant.
- Only you can turn it on, by saying "turn on the camera". The assistant
  first explains what the camera does and waits for you to say "confirm".
- The assistant itself is blocked, in code, from switching the camera on.
  If it tries to change that setting, the attempt is refused.
- When the camera is on, a photo is taken **only when you ask** ("what am
  I holding", "read this"). It never watches or records video.
- Only the most recent photo is kept on your computer, in the
  `state/camera` folder inside the assistant's folder. Say "delete my
  photos" to remove it, or "turn off the camera" to switch the camera off
  and delete the photos at the same time.

## What leaves your computer, and where it goes

| What | Where it goes | Why |
|---|---|---|
| Your microphone audio | **Nowhere.** It is turned into text on your computer. | Speech recognition runs locally. |
| What you say or type (as text), and any photo you ask about | Anthropic (Claude), under **your own** Claude account | So Claude can answer. Anthropic's privacy policy and your account settings apply. |
| The assistant's spoken replies (as text) | ElevenLabs, **only if you turned on** an ElevenLabs voice with your own key | To make the voice. The free built-in voices run entirely on your computer. |
| Anything else (email, calendar, web pages) | Only the services **you** connect, under **your** accounts | Only when you set them up. |

The speech models are downloaded once, at install time, from Hugging
Face. After that, hearing and the built-in voices work offline.

## What is saved on your computer

- Daily transcripts of your conversations, if you chose a transcript folder
  during setup (plain text, so you can re-read them). Passwords, keys and
  card numbers are blanked out before anything is written.
- A log of the actions the assistant took, in the `logs` folder.
- Your settings, in `backtalk.json`.
- The latest camera photo, only if the camera is on.

All of it stays on your computer. You can delete any of it at any time;
the assistant will keep working.

## Questions

If anything here is unclear, or you think the assistant did something
this page says it doesn't, please open an issue on this repository.
