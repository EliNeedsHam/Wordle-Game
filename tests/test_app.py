from app import create_app


def make_app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATA_PATH": tmp_path / "test.sqlite3",
            "GIF_SEARCH_ENABLED": False,
            "SECRET_KEY": "test",
        }
    )
    app.extensions["wordforge_answers"][:] = ["crane"]
    app.extensions["wordforge_accepted_words"].update(
        {"crane", "slate", "brick", "plant", "house", "night", "world"}
    )
    return app


def create_profile(client, name="Ada"):
    response = client.post("/api/profiles", json={"name": name})
    assert response.status_code == 201
    return response.get_json()["profile"]


def test_profile_creation_and_selection(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    profile = create_profile(client)
    response = client.get("/api/profiles")

    assert response.status_code == 200
    body = response.get_json()
    assert body["profiles"][0]["name"] == "Ada"
    assert body["current_profile_id"] == profile["id"]


def test_duplicate_profile_names_are_rejected(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    create_profile(client, "Ada")
    response = client.post("/api/profiles", json={"name": "ada"})

    assert response.status_code == 400
    assert "already exists" in response.get_json()["error"]


def test_new_game_and_winning_guess_update_stats(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    create_profile(client)

    game_response = client.post("/api/games", json={})
    assert game_response.status_code == 201
    assert game_response.get_json()["game"]["status"] == "active"

    guess_response = client.post("/api/games/current/guesses", json={"guess": "crane"})
    assert guess_response.status_code == 200
    game = guess_response.get_json()["game"]
    assert game["status"] == "won"
    assert game["answer"] == "crane"
    assert "gif_url" in game

    stats = client.get("/api/stats").get_json()["stats"]
    assert stats["games_played"] == 1
    assert stats["wins"] == 1
    assert stats["current_streak"] == 1
    assert stats["guess_distribution"]["1"] == 1


def test_invalid_guess_is_rejected_without_consuming_attempt(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    create_profile(client)
    client.post("/api/games", json={})

    response = client.post("/api/games/current/guesses", json={"guess": "zzzzz"})

    assert response.status_code == 400
    assert response.get_json()["game"]["guess_count"] == 0


def test_common_dictionary_word_is_accepted_by_api(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    create_profile(client)
    client.post("/api/games", json={})

    response = client.post("/api/games/current/guesses", json={"guess": "farts"})

    assert response.status_code == 200
    assert response.get_json()["game"]["guess_count"] == 1


def test_losing_game_updates_loss_stats(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    create_profile(client)
    client.post("/api/games", json={})

    for word in ["slate", "brick", "plant", "house", "night", "world"]:
        response = client.post("/api/games/current/guesses", json={"guess": word})

    game = response.get_json()["game"]
    assert game["status"] == "lost"
    assert game["answer"] == "crane"

    stats = client.get("/api/stats").get_json()["stats"]
    assert stats["games_played"] == 1
    assert stats["wins"] == 0
    assert stats["losses"] == 1
    assert stats["current_streak"] == 0


def test_stats_are_profile_specific(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    ada = create_profile(client, "Ada")
    client.post("/api/games", json={})
    client.post("/api/games/current/guesses", json={"guess": "crane"})

    bob = client.post("/api/profiles", json={"name": "Bob"}).get_json()["profile"]
    bob_stats = client.get("/api/stats").get_json()["stats"]

    client.post("/api/session/profile", json={"profile_id": ada["id"]})
    ada_stats = client.get("/api/stats").get_json()["stats"]

    assert bob["id"] != ada["id"]
    assert bob_stats["games_played"] == 0
    assert ada_stats["games_played"] == 1


def test_gif_url_is_hidden_until_game_completion(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    app.config["GIF_SEARCH_ENABLED"] = True
    monkeypatch.setattr("app.find_gif_url", lambda answer: f"https://example.test/{answer}.gif")
    client = app.test_client()
    create_profile(client)

    active_game = client.post("/api/games", json={}).get_json()["game"]
    assert "answer" not in active_game
    assert "gif_url" not in active_game

    completed_game = client.post("/api/games/current/guesses", json={"guess": "crane"}).get_json()[
        "game"
    ]
    assert completed_game["answer"] == "crane"
    assert completed_game["gif_url"] == "https://example.test/crane.gif"
