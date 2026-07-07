from app.words import load_words


def test_common_five_letter_guesses_are_accepted():
    _answers, guesses = load_words()

    assert "bored" in guesses
    assert "farts" in guesses
