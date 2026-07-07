import random
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

from .gif_search import find_gif_url
from .game import GameError, MAX_GUESSES, keyboard_states, score_guess, validate_guess
from .storage import DEFAULT_DATA_PATH, Store
from .words import load_words


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_mapping(
        SECRET_KEY="dev-wordforge-local",
        DATA_PATH=DEFAULT_DATA_PATH,
        GIF_SEARCH_ENABLED=True,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    store = Store(app.config["DATA_PATH"])
    app.extensions["wordforge_store"] = store
    answers, accepted_words = load_words()
    app.extensions["wordforge_answers"] = answers
    app.extensions["wordforge_accepted_words"] = accepted_words

    def current_words():
        answers, accepted_words = load_words()
        app.extensions["wordforge_answers"] = answers
        app.extensions["wordforge_accepted_words"] = accepted_words
        return answers, accepted_words

    def current_profile_id():
        profile_id = session.get("profile_id")
        if profile_id and store.get_profile(profile_id):
            return profile_id
        return None

    def require_profile():
        profile_id = current_profile_id()
        if not profile_id:
            return None, (jsonify({"error": "Select or create a profile first."}), 401)
        return profile_id, None

    def public_game(game, reveal_answer=False):
        if not game:
            return None
        guesses = game["guesses"]
        payload = {
            "id": game["id"],
            "status": game["status"],
            "guess_count": len(guesses),
            "max_guesses": MAX_GUESSES,
            "guesses": guesses,
            "keyboard": keyboard_states(guesses),
            "created_at": game["created_at"],
        }
        if reveal_answer or game["status"] in {"won", "lost"}:
            payload["answer"] = game["answer"]
            payload["gif_url"] = game.get("gif_url")
        return payload

    def create_random_game(profile_id):
        answers, _accepted_words = current_words()
        answer = random.choice(answers)
        gif_url = find_gif_url(answer) if app.config["GIF_SEARCH_ENABLED"] else None
        return store.create_game(profile_id, answer, gif_url)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/profiles")
    def profiles():
        return jsonify(
            {
                "profiles": store.list_profiles(),
                "current_profile_id": current_profile_id(),
            }
        )

    @app.post("/api/profiles")
    def create_profile():
        data = request.get_json(silent=True) or {}
        try:
            profile = store.create_profile(data.get("name"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        session["profile_id"] = profile["id"]
        return jsonify({"profile": profile}), 201

    @app.post("/api/session/profile")
    def select_profile():
        data = request.get_json(silent=True) or {}
        profile_id = data.get("profile_id")
        profile = store.get_profile(profile_id)
        if not profile:
            return jsonify({"error": "Profile not found."}), 404
        session["profile_id"] = profile["id"]
        return jsonify({"profile": profile})

    @app.post("/api/games")
    def create_game():
        profile_id, error = require_profile()
        if error:
            return error
        game = create_random_game(profile_id)
        return jsonify({"game": public_game(game)}), 201

    @app.get("/api/games/current")
    def current_game():
        profile_id, error = require_profile()
        if error:
            return error
        game = store.get_current_game(profile_id)
        if not game:
            game = create_random_game(profile_id)
        return jsonify({"game": public_game(game)})

    @app.post("/api/games/current/guesses")
    def submit_guess():
        profile_id, error = require_profile()
        if error:
            return error
        game = store.get_current_game(profile_id)
        if not game:
            game = create_random_game(profile_id)
        if game["status"] != "active":
            return jsonify({"error": "This game is already complete.", "game": public_game(game)}), 400

        data = request.get_json(silent=True) or {}
        try:
            _answers, accepted_words = current_words()
            guess = validate_guess(data.get("guess"), accepted_words)
            pattern = score_guess(game["answer"], guess)
        except GameError as exc:
            return jsonify({"error": str(exc), "game": public_game(game)}), 400

        game = store.add_guess(game["id"], guess, pattern)
        if guess == game["answer"]:
            game = store.complete_game(game["id"], "won", len(game["guesses"]))
        elif len(game["guesses"]) >= MAX_GUESSES:
            game = store.complete_game(game["id"], "lost", len(game["guesses"]))

        return jsonify({"game": public_game(game)})

    @app.get("/api/stats")
    def stats():
        profile_id, error = require_profile()
        if error:
            return error
        return jsonify({"stats": store.stats_for_profile(profile_id)})

    return app
