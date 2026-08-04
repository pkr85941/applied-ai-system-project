"""
Tests for the deterministic pieces of the agentic layer (src/agent.py).

These cover the parts that must behave predictably without any network / LLM call:
the input-validation guardrail, the catalog summary, the no-credentials keyword
fallback, and the tool dispatcher. The Claude-driven loop itself is not tested here
because it requires live API credentials.
"""

from src.agent import (
    _execute_tool,
    _keyword_profile,
    _validate_profile,
    catalog_summary,
)
from src.recommender import load_songs

import json


def small_catalog():
    return [
        {
            "id": 1, "title": "Test Pop", "artist": "A", "genre": "pop", "mood": "happy",
            "energy": 0.8, "tempo_bpm": 120, "valence": 0.9, "danceability": 0.8, "acousticness": 0.2,
        },
        {
            "id": 2, "title": "Test Lofi", "artist": "B", "genre": "lofi", "mood": "chill",
            "energy": 0.4, "tempo_bpm": 80, "valence": 0.6, "danceability": 0.5, "acousticness": 0.9,
        },
    ]


def test_validate_profile_clamps_and_coerces():
    # Out-of-range energy is clamped; bad k falls back; strings are lowercased.
    profile = _validate_profile(
        {"favorite_genre": "POP", "favorite_mood": "Happy", "target_energy": 5.0, "likes_acoustic": 1}
    )
    assert profile["genre"] == "pop"
    assert profile["mood"] == "happy"
    assert profile["energy"] == 1.0            # clamped from 5.0
    assert profile["likes_acoustic"] is True
    assert 1 <= profile["k"] <= 10


def test_validate_profile_handles_garbage_energy():
    profile = _validate_profile({"target_energy": "not-a-number"})
    assert profile["energy"] == 0.5            # safe default


def test_catalog_summary_reports_genres_and_moods():
    summary = catalog_summary(small_catalog())
    assert summary["song_count"] == 2
    assert summary["genres"] == ["lofi", "pop"]
    assert "happy" in summary["moods"] and "chill" in summary["moods"]
    assert summary["energy_min"] == 0.4 and summary["energy_max"] == 0.8


def test_keyword_profile_reads_genre_mood_energy_and_acoustic():
    songs = load_songs("data/songs.csv")
    profile = _keyword_profile("intense rock for the gym", songs)
    assert profile["genre"] == "rock"
    assert profile["mood"] == "intense"
    assert profile["energy"] == 0.9            # "gym" is a hype cue
    assert profile["likes_acoustic"] is False


def test_keyword_profile_detects_acoustic_and_calm():
    songs = load_songs("data/songs.csv")
    profile = _keyword_profile("chill acoustic lofi for studying", songs)
    assert profile["likes_acoustic"] is True
    assert profile["energy"] == 0.3            # "chill"/"study" are calm cues


def test_execute_tool_recommend_returns_grounded_results():
    songs = small_catalog()
    raw = _execute_tool(
        "recommend_songs",
        {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8, "likes_acoustic": False},
        songs,
    )
    payload = json.loads(raw)
    assert payload["results"][0]["title"] == "Test Pop"   # best match ranks first
    # Every returned song must be a real catalog title (the engine never invents songs).
    titles = {s["title"] for s in songs}
    assert all(r["title"] in titles for r in payload["results"])


def test_execute_tool_catalog_summary():
    payload = json.loads(_execute_tool("get_catalog_summary", {}, small_catalog()))
    assert payload["song_count"] == 2


def test_execute_tool_unknown_returns_error():
    payload = json.loads(_execute_tool("does_not_exist", {}, small_catalog()))
    assert "error" in payload
