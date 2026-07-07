from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORDS_DIR = ROOT / "data" / "words"
_CACHE = {"signature": None, "answers": None, "guesses": None}


def _load_word_file(path):
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        word = line.strip().lower()
        if len(word) == 5 and word.isalpha():
            words.append(word)
    return words


def load_words():
    answer_path = WORDS_DIR / "answers.txt"
    guesses_path = WORDS_DIR / "guesses.txt"
    signature = (
        answer_path.stat().st_mtime_ns,
        guesses_path.stat().st_mtime_ns,
    )
    if _CACHE["signature"] == signature:
        return _CACHE["answers"], _CACHE["guesses"]

    answers = _load_word_file(WORDS_DIR / "answers.txt")
    guesses = set(_load_word_file(WORDS_DIR / "guesses.txt"))
    guesses.update(answers)
    _CACHE.update({"signature": signature, "answers": answers, "guesses": guesses})
    return answers, guesses
