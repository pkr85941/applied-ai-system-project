"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from src.recommender import load_songs, recommend_songs

# Regular taste profiles
PROFILES = {
    "High-Energy Pop": {"genre": "pop", "mood": "happy", "energy": 0.9},
    "Chill Lofi": {"genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True},
    "Deep Intense Rock": {"genre": "rock", "mood": "intense", "energy": 0.9},
    # Adversarial / edge-case profiles: designed to probe conflicting or unmatched preferences
    "Adversarial: Sad but High-Energy Metal": {"genre": "metal", "mood": "sad", "energy": 0.9},
    "Adversarial: Genre Not In Catalog": {"genre": "opera", "mood": "happy", "energy": 0.5},
}


def print_recommendations(label: str, user_prefs: dict, songs: list, k: int = 5) -> None:
    """Prints the top k ranked recommendations for one named user profile."""
    print(f"=== {label} ===")
    print(f"Profile: {user_prefs}\n")
    recommendations = recommend_songs(user_prefs, songs, k=k)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"{rank}. {song['title']} by {song['artist']} - Score: {score:.2f}")
        print(f"   Because: {explanation}")
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    for label, user_prefs in PROFILES.items():
        print_recommendations(label, user_prefs, songs, k=5)


if __name__ == "__main__":
    main()
