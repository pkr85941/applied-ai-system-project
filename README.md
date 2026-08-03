# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

**VibeFinder 1.0** is a content-based recommender over an 18-song catalog. A listener
states a favorite genre, favorite mood, target energy, and whether they like acoustic
songs; the system scores every song with a weighted point system (genre match, mood
match, energy closeness, acoustic bonus) and returns the top matches with a
plain-language explanation of why each song scored the way it did.

---

## How The System Works

Real-world recommenders (Spotify, YouTube, etc.) don't just look at one song at a
time. At scale they combine **content signals** (the actual properties of a song —
genre, tempo, energy) with **behavioral signals** (what millions of similar listeners
skipped, replayed, or added to playlists) and learn patterns automatically. My version
is a much smaller, transparent stand-in for the *content-based* half of that idea: it
compares the measurable properties of each song to a user's stated taste and scores how
well they match. It deliberately prioritizes the "vibe" of a song — how energetic and
how positive it feels, plus its genre and mood — over popularity or listening history,
because those are the features that a person can actually feel and describe.

### Features each `Song` uses

- `genre` — categorical anchor (pop, lofi, rock, jazz, ambient…)
- `mood` — categorical vibe label (happy, chill, intense, focused…)
- `energy` — numeric 0–1, how hyped vs. calm the song is
- `valence` — numeric 0–1, musical positivity / happiness

(The dataset also has `tempo_bpm`, `danceability`, and `acousticness`, which are good
candidates for later experiments.)

### What the `UserProfile` stores

The user's preferences, matching the fields implemented in `src/recommender.py`:

- `favorite_genre` (e.g. `"lofi"`)
- `favorite_mood` (e.g. `"chill"`)
- `target_energy` — a target value 0–1, e.g. `0.35`
- `likes_acoustic` — a boolean, `True`/`False`

(Early planning considered a `valence` target too, but the finalized recipe below
uses `likes_acoustic` + `acousticness` instead — see the Algorithm Recipe.)

### How the `Recommender` scores a song (Scoring Rule)

For **categorical** features it awards points for an exact match. For **numeric**
features it rewards *closeness* to the user's target rather than "bigger is better":

```
feature_score = 1 - |song_value - user_preference|      # for energy
```

Everything is combined with weights so some features matter more than others:

```
score = w_genre  · (genre matches?)
      + w_mood   · (mood matches?)
      + w_energy · (1 - |energy - target_energy|)
      + acoustic_bonus · (likes_acoustic and acousticness > threshold?)
```

Genre is weighted highest, mood a bit lower, and energy closeness around 1.0, with a
small conditional bonus for acoustic-loving users — see the finalized weights below.

### How songs get chosen (Ranking Rule)

The Scoring Rule gives one number per song. The Ranking Rule then sorts **all** songs
by that score (highest first) and returns the top N. Both rules are needed: scoring
judges a single song, while ranking makes the comparative decision across the whole
catalog — which is what a recommendation actually is.

### Example `UserProfile`

```python
UserProfile(
    favorite_genre="lofi",
    favorite_mood="chill",
    target_energy=0.35,
    likes_acoustic=True,
)
```

Checked against the catalog, this profile clearly separates a match like *Midnight
Coding* (lofi, chill, energy 0.42, acousticness 0.71 → near-top score) from a mismatch
like *Broken Mirror* (metal, aggressive, energy 0.97, acousticness 0.05 → near-bottom
score). It does **not** distinguish well between two songs of the *same* genre with
different moods, since genre carries the most weight — a known limitation, not a bug.

### Finalized Algorithm Recipe

| Rule | Points |
|---|---|
| Genre match | `+2.0` |
| Mood match | `+1.5` |
| Energy similarity | `+1.0 × (1 - \|song.energy - target_energy\|)` |
| Acoustic bonus | `+0.5` if `likes_acoustic` is `True` and `song.acousticness > 0.6` |

Genre outweighs mood because it's the strongest "right bucket / wrong bucket" signal;
energy is a continuous reward rather than a flat bonus since it's a closeness measure;
the acoustic bonus is small and conditional since it only matters to some users.

### Data Flow

```mermaid
flowchart LR
    A[User Profile\nfavorite_genre, favorite_mood,\ntarget_energy, likes_acoustic] --> C
    B[songs.csv\none row per song] --> C
    C[Loop: score_song\nfor every song] --> D[Ranking\nsort by score, take top K]
    D --> E[Top K Recommendations]
```

### Expected Biases

- **Genre dominance**: because genre is worth the most points, a song in the "right"
  genre but a mismatched mood can still outrank a song in the "wrong" genre with a
  perfect mood/energy match. The system may over-prioritize genre and miss great
  cross-genre matches.
- **Small, hand-picked catalog**: 18 songs across ~13 genres means most genres have
  only 1–2 songs, so results are heavily constrained by whatever happens to exist in
  the CSV rather than a true "best match."
- **No history/collaborative signal**: unlike real systems, this recommender has no
  idea what similar users liked — it can only compare stated preferences to song
  metadata, so it will keep recommending the same kind of song forever and can't
  surprise the user with something outside their stated taste.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Output of `python -m src.main` for the default profile (`genre=pop, mood=happy, energy=0.8`):

```
Loaded songs: 18

Top recommendations:

1. Sunrise City by Neon Echo - Score: 4.48
   Because: genre match (+2.0), mood match (+1.5), energy similarity (+0.98)

2. Gym Hero by Max Pulse - Score: 2.87
   Because: genre match (+2.0), energy similarity (+0.87)

3. Rooftop Lights by Indigo Parade - Score: 2.46
   Because: mood match (+1.5), energy similarity (+0.96)

4. Concrete Bloom by Kid Static - Score: 1.00
   Because: energy similarity (+1.00)

5. Night Drive Loop by Neon Echo - Score: 0.95
   Because: energy similarity (+0.95)
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

**Weight shift: halved genre (2.0 → 1.0), doubled energy (1.0 → 2.0).**

For most profiles the #1 result didn't change — the winning song was usually strong
enough on genre+mood+energy together that halving genre alone didn't flip first
place. But the *order below #1* shifted noticeably. For "High-Energy Pop," *Rooftop
Lights* (genre mismatch, mood+energy match) jumped from #3 to #2, passing *Gym Hero*
(genre match only) — because a strong energy match started outweighing a lone genre
match. Same pattern in "Chill Lofi": *Spacewalk Thoughts* (mood+energy match, no
genre) passed *Focus Flow* (genre+energy match, no mood).

**Conclusion:** this made recommendations *more energy-driven and less genre-locked*,
not objectively "more accurate" — it depends entirely on whether you believe genre or
energy should dominate a listener's vibe. It confirmed the system is sensitive to
weight changes exactly where you'd expect: near-tied songs re-rank, while a clear
best-match song stays on top regardless. See [model_card.md](model_card.md) for the
full adversarial-profile evaluation and observed biases.

---

## Limitations and Risks

- It only works on a tiny, hand-picked catalog of 18 songs, most genres having just
  1–3 tracks, so results are limited by what happens to exist in the CSV rather than a
  true "best match" across real-world music.
- It does not understand lyrics, artist popularity, or listening history — only the
  numeric/categorical tags in the CSV.
- Genre is the heaviest-weighted signal, so it can over-favor a matching genre even
  when a mismatched-genre song would actually feel closer to the user's mood/energy.
- It cannot detect contradictory preferences (e.g. `genre=metal, mood=sad`) — it just
  maximizes whatever score is available and returns a confident top 5 regardless.

See [model_card.md](model_card.md) for the full evaluation, including adversarial
profiles that surfaced these issues directly.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Building this showed me that a "recommendation" is really just scoring plus sorting —
there's no hidden intelligence in between. Once every song has a single number, the
ranking step is almost trivial; the real design work is deciding which features to
compare and how much weight to give each one. That also means bias enters at the
weighting stage, not some mysterious later step: because I weighted genre highest, the
system will always favor "right genre, wrong everything else" over "wrong genre, right
everything else," which is a value judgment I made, not a fact about music.

Testing adversarial profiles made the unfairness risk concrete. When I gave the system
a contradictory profile (`genre=metal, mood=sad, energy=0.9`), it confidently
recommended an aggressive-sounding song anyway — it has no way to notice that a
request doesn't make sense, so it will always produce a top 5, even when none of them
are a good fit. A real system with more data and more users could hide this same
flaw much better, which is exactly why it's worth understanding at this small, visible
scale first.



