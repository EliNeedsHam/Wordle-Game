import pytest

from app.game import GameError, keyboard_states, score_guess, validate_guess


def test_score_guess_marks_correct_present_and_absent():
    assert score_guess("crane", "candy") == [
        "correct",
        "present",
        "present",
        "absent",
        "absent",
    ]


def test_score_guess_handles_duplicate_letters():
    assert score_guess("apple", "allee") == [
        "correct",
        "present",
        "absent",
        "absent",
        "correct",
    ]


def test_validate_guess_requires_dictionary_word():
    with pytest.raises(GameError, match="dictionary"):
        validate_guess("zzzzz", {"crane"})


def test_validate_guess_normalizes_valid_words():
    assert validate_guess(" CRANE ", {"crane"}) == "crane"


def test_keyboard_states_keep_best_letter_quality():
    guesses = [
        {"word": "candy", "pattern": ["present", "absent", "absent", "absent", "absent"]},
        {"word": "crane", "pattern": ["correct", "correct", "correct", "correct", "correct"]},
    ]
    states = keyboard_states(guesses)
    assert states["c"] == "correct"
    assert states["d"] == "absent"
