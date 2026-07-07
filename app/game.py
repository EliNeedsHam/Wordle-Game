from collections import Counter


MAX_GUESSES = 6
WORD_LENGTH = 5


class GameError(ValueError):
    """Raised when a guess cannot be accepted."""


def normalize_word(word):
    return (word or "").strip().lower()


def score_guess(answer, guess):
    answer = normalize_word(answer)
    guess = normalize_word(guess)
    if len(answer) != WORD_LENGTH or len(guess) != WORD_LENGTH:
        raise GameError("Both answer and guess must be five letters.")

    result = ["absent"] * WORD_LENGTH
    remaining = Counter()

    for index, letter in enumerate(guess):
        if answer[index] == letter:
            result[index] = "correct"
        else:
            remaining[answer[index]] += 1

    for index, letter in enumerate(guess):
        if result[index] == "correct":
            continue
        if remaining[letter] > 0:
            result[index] = "present"
            remaining[letter] -= 1

    return result


def validate_guess(guess, accepted_words):
    guess = normalize_word(guess)
    if len(guess) != WORD_LENGTH:
        raise GameError("Guess must be exactly five letters.")
    if not guess.isalpha():
        raise GameError("Guess can only contain letters.")
    if guess not in accepted_words:
        raise GameError("That word is not in the dictionary.")
    return guess


def keyboard_states(guesses):
    rank = {"absent": 1, "present": 2, "correct": 3}
    states = {}
    for guess in guesses:
        for letter, state in zip(guess["word"], guess["pattern"]):
            current = states.get(letter)
            if current is None or rank[state] > rank[current]:
                states[letter] = state
    return states
