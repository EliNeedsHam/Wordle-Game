# WordForge

WordForge is a local-first, dark-mode Flask Wordle game with named profiles,
persistent stats, animated tiles, and a strict 5-letter dictionary.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python run.py
```

Open http://127.0.0.1:5000 and create a profile to start playing.

## Test

```bash
python -m pytest
```

## Gameplay

- Every game randomly chooses a 5-letter answer from `data/words/answers.txt`.
- When a game starts, the backend searches for a GIF using the answer as the search term.
- The answer GIF is revealed only after a win or loss, alongside the result animation.
- Guesses must be valid words from `data/words/guesses.txt`.
- Each named profile stores its own local stats in `instance/wordforge.sqlite3`.
- Starting a new game abandons any active unfinished game for the current profile.
- If GIF search is offline or times out, the game still works and simply skips the GIF.
