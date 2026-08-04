# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeFinder 2.0** — an agentic music recommender that extends **VibeFinder 1.0** (my
Module 1–3 content-based scoring engine) with an AI planning layer powered by Claude.
The responsible-AI reflection for the Module 4 agentic system is in
[Section 10](#10-responsible-ai-reflection-module-4).

---

## 2. Intended Use  

VibeFinder suggests songs from a small, fixed catalog based on a listener's stated
taste — a favorite genre, a favorite mood, a target energy level, and whether they
like acoustic-sounding songs. It's built for classroom exploration, not real users: it
assumes the listener already knows and can name their own taste in these exact terms,
which most real people can't do off the top of their head. It's a teaching tool for
understanding how content-based scoring works, not a production recommender.

**Not intended for:** real-world music recommendation, any product with real users, or
any decision that matters (e.g. don't use this to judge whether a song or artist is
"good"). It has no listening history, no collaborative signal, and only 18 songs, so it
cannot generalize beyond this toy catalog and should not be presented to a user as
understanding their actual taste.

---

## 3. How the Model Works  

Every song has a genre, a mood, and some numbers describing how energetic, upbeat,
danceable, and acoustic it sounds. A listener tells the system their favorite genre,
favorite mood, a target energy level, and whether they like acoustic songs. VibeFinder
then goes through every song in the catalog one at a time and hands out points: 2
points if the genre matches exactly, 1.5 points if the mood matches exactly, up to 1
point for how close the song's energy is to what the listener wants (a perfect match
gets the full point, and it shrinks the further apart they are), and half a point extra
if the listener likes acoustic songs and this song sounds acoustic enough. It adds all
of that up into one score per song, then lines every song up from the highest score to
the lowest and hands back the top few. The starter code only had placeholder functions
with no actual scoring — the whole point-based system, the "why did this song get this
score" explanations, and the ranking/sorting step are what I built on top of it.

---

## 4. Data  

The catalog has 18 songs (I started with 10 and added 8 more). Between them, they cover
13 genres (pop, lofi, rock, ambient, jazz, synthwave, indie pop, hip-hop, folk, metal,
classical, r&b, reggaeton, punk) and moods ranging from happy and chill to intense,
moody, sad, and angry. Most genres only have 1–3 songs each, so the catalog is wide but
shallow — it can represent many different vibes but can't offer much variety *within*
any one of them. It also has no lyrics, no artist popularity, no listening history, and
no way to represent a song that blends multiple genres or moods, so any taste that
depends on those things is invisible to this system.

---

## 5. Strengths  

VibeFinder gives sensible results when a listener's preferences line up cleanly with
one clear genre and mood in the catalog — for example, "pop / happy / high energy"
correctly surfaces upbeat pop songs first, and "lofi / chill / low energy" correctly
surfaces quiet lofi tracks first (see Evaluation below). The energy-similarity math
also behaves the way I'd expect: songs closest to the target energy consistently
outscore songs far from it, even when they don't match on genre or mood at all. And
because it prints the point breakdown for every song, I could always tell *why* a song
ranked where it did — that transparency is the system's biggest strength over a
"black box" score.

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

During evaluation (see below), the "Adversarial: Sad but High-Energy Metal" profile
(`genre=metal, mood=sad, energy=0.9`) exposed a real weakness: the top recommendation
was *Broken Mirror*, a metal song whose mood is tagged **aggressive**, not sad. The
system never checks whether a song can satisfy a user's *contradictory* preferences at
once — it just adds up whatever points are available (genre + energy here), so a
genre/energy match can outrank a song that would actually feel right emotionally. In
other words, the scoring rule has no concept of "this user's request doesn't make
sense together," which real recommenders also struggle with but often hide better.
A second bias shows up with `favorite_genre="opera"` (a genre entirely absent from the
catalog): the system quietly falls back to mood+energy matches without ever signaling
"no genre match exists," which could mislead a user into thinking the system
understood their taste when it actually just ignored it. Finally, because
`GENRE_WEIGHT` (2.0) is the single largest score component and only 1–3 songs exist
per genre in this catalog, users with a favorite_genre that overlaps a genre-heavy
song (like the two "Neon Echo" pop tracks) will keep seeing the same artist recur near
the top, which is a small-dataset "filter bubble" more than a true taste signal.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

I tested five profiles: three realistic ("High-Energy Pop," "Chill Lofi," "Deep
Intense Rock") and two adversarial ones designed to probe edge cases ("Sad but
High-Energy Metal" and "Genre Not In Catalog"). Output for all five, from
`python -m src.main` with the finalized weights (genre +2.0, mood +1.5, energy
closeness up to +1.0, acoustic bonus +0.5), is below.

```
=== High-Energy Pop ===
Profile: {'genre': 'pop', 'mood': 'happy', 'energy': 0.9}

1. Sunrise City by Neon Echo - Score: 4.42
   Because: genre match (+2.0), mood match (+1.5), energy similarity (+0.92)
2. Gym Hero by Max Pulse - Score: 2.97
   Because: genre match (+2.0), energy similarity (+0.97)
3. Rooftop Lights by Indigo Parade - Score: 2.36
   Because: mood match (+1.5), energy similarity (+0.86)
4. Storm Runner by Voltline - Score: 0.99
   Because: energy similarity (+0.99)
5. Isla Nocturna by Ritmo Sol - Score: 0.96
   Because: energy similarity (+0.96)

=== Chill Lofi ===
Profile: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.35, 'likes_acoustic': True}

1. Library Rain by Paper Lanterns - Score: 5.00
   Because: genre match (+2.0), mood match (+1.5), energy similarity (+1.00), acoustic bonus (+0.5)
2. Midnight Coding by LoRoom - Score: 4.93
   Because: genre match (+2.0), mood match (+1.5), energy similarity (+0.93), acoustic bonus (+0.5)
3. Focus Flow by LoRoom - Score: 3.45
   Because: genre match (+2.0), energy similarity (+0.95), acoustic bonus (+0.5)
4. Spacewalk Thoughts by Orbit Bloom - Score: 2.93
   Because: mood match (+1.5), energy similarity (+0.93), acoustic bonus (+0.5)
5. Coffee Shop Stories by Slow Stereo - Score: 1.48
   Because: energy similarity (+0.98), acoustic bonus (+0.5)

=== Deep Intense Rock ===
Profile: {'genre': 'rock', 'mood': 'intense', 'energy': 0.9}

1. Storm Runner by Voltline - Score: 4.49
   Because: genre match (+2.0), mood match (+1.5), energy similarity (+0.99)
2. Gym Hero by Max Pulse - Score: 2.47
   Because: mood match (+1.5), energy similarity (+0.97)
3. Isla Nocturna by Ritmo Sol - Score: 0.96
   Because: energy similarity (+0.96)
4. Riot in My Chest by The Static Kids - Score: 0.95
   Because: energy similarity (+0.95)
5. Broken Mirror by Wraith Choir - Score: 0.93
   Because: energy similarity (+0.93)

=== Adversarial: Sad but High-Energy Metal ===
Profile: {'genre': 'metal', 'mood': 'sad', 'energy': 0.9}

1. Broken Mirror by Wraith Choir - Score: 2.93
   Because: genre match (+2.0), energy similarity (+0.93)
2. Heartbreak Hotel Room by Nadia Cruz - Score: 1.93
   Because: mood match (+1.5), energy similarity (+0.43)
3. Storm Runner by Voltline - Score: 0.99
   Because: energy similarity (+0.99)
4. Gym Hero by Max Pulse - Score: 0.97
   Because: energy similarity (+0.97)
5. Isla Nocturna by Ritmo Sol - Score: 0.96
   Because: energy similarity (+0.96)

=== Adversarial: Genre Not In Catalog ===
Profile: {'genre': 'opera', 'mood': 'happy', 'energy': 0.5}

1. Rooftop Lights by Indigo Parade - Score: 2.24
   Because: mood match (+1.5), energy similarity (+0.74)
2. Sunrise City by Neon Echo - Score: 2.18
   Because: mood match (+1.5), energy similarity (+0.68)
3. Midnight Coding by LoRoom - Score: 0.92
   Because: energy similarity (+0.92)
4. Focus Flow by LoRoom - Score: 0.90
   Because: energy similarity (+0.90)
5. Coffee Shop Stories by Slow Stereo - Score: 0.87
   Because: energy similarity (+0.87)
```

**Profile-to-profile comparisons:**

- **High-Energy Pop vs. Chill Lofi** — completely different top songs and completely
  different feel (upbeat pop vocals vs. quiet lofi loops), which makes sense: the two
  profiles share no genre, no mood, and target opposite ends of the energy scale, so
  every scoring component pushes toward different songs.
- **Deep Intense Rock vs. High-Energy Pop** — both want energy around 0.9, so the
  *runner-up* lists overlap on high-energy tracks like "Gym Hero," but the winner
  differs (rock vs. pop) because genre is weighted the heaviest. This confirms energy
  alone isn't enough to define a "vibe" — genre still anchors the identity of the
  recommendation.
- **Deep Intense Rock vs. Sad-but-High-Energy Metal** — both surfaced songs from the
  "aggressive/intense" cluster at the top, even though one profile asked for `sad`.
  This was the most surprising result: the system doesn't recognize that "metal" +
  "sad" is an unusual combination in real life, and it doesn't try to reconcile the
  conflict — it just maximizes whatever score is available, landing on an aggressive
  song for a self-described "sad" listener.
- **Genre Not In Catalog** — with no genre in the catalog to match "opera," the
  system gracefully falls back to mood/energy-only scoring rather than crashing or
  returning nothing, which is a strength, but it also means the user never finds out
  their stated genre had zero effect on the results.

In plain language: a song like "Gym Hero" keeps showing up for "Happy Pop" listeners
not because the system understands happiness, but because it is a pop song with high
energy — two of the three things this simple scorer actually checks. If two different
users both say "pop" and "high energy," they will get very similar top results even
if their personal sense of "happy" differs, because the system has no way to measure
happiness beyond the `mood` label and the `valence` number it isn't even using yet.

---

## 8. Future Work  

If I kept developing this, I'd:

1. **Use `valence` in the score.** Right now "happy" vs. "sad" only exists as a mood
   label, but the catalog already has a 0–1 valence number for actual musical
   positivity — adding it as a closeness score (like energy) would let the system
   distinguish "happy" listeners more precisely instead of relying on an exact string
   match.
2. **Detect and flag unmatched preferences.** When a user's genre isn't in the catalog
   at all, or their mood+energy combo is unusual (like sad+high-energy), the system
   should say so explicitly ("no songs matched your genre exactly") instead of
   silently falling back to a partial score.
3. **Add a diversity rule to the ranking step.** Right now the top 5 can include two
   songs by the same artist (as it nearly did with "Neon Echo"); capping results per
   artist or genre would make the top 5 feel less repetitive on a small catalog.

---

## 9. Personal Reflection  

The biggest learning moment was realizing that "recommendation" is really just
"scoring + sorting" — there's no magic in between. Once I had a number per song, the
hard design work was already done; the ranking step is almost trivial. What surprised
me most was how *convincing* a simple weighted-sum score can feel: seeing "Sunrise
City" show up first for a "pop / happy / high energy" listener, with a clear
point-by-point explanation, genuinely felt like a real recommendation, even though the
math behind it is just addition and absolute-value differences.

AI tools helped me move fast on the mechanical parts — writing the CSV loader, wiring
up the dataclasses, generating diverse extra songs for the catalog — but I had to
double-check anything involving the actual scoring logic and the starter code's
existing interfaces. For example, `main.py`'s original import (`from recommender
import ...`) looked fine on the surface but silently failed under `python -m
src.main`; I only caught it by actually running the code rather than trusting that it
would work. That was a good reminder that AI-suggested code needs to be run and
tested, not just read.

The adversarial testing phase changed how I think about recommendation apps the most.
Feeding in a deliberately contradictory profile (sad + high-energy metal) and watching
the system confidently recommend an aggressive song taught me that these systems don't
"understand" anything — they optimize whatever signal is available, even when that
signal doesn't add up to something coherent. If I extended this project, I'd want to
build in some way for the system to notice and communicate when a user's preferences
don't have a good match, rather than always returning a confident top 5 regardless.

---

## 10. Responsible AI Reflection (Module 4)

This section is the responsible-AI reflection for **VibeFinder 2.0**, the agentic layer
([`src/agent.py`](src/agent.py)) that lets a listener make requests in plain language and
has Claude plan a taste profile, call the deterministic scoring engine as a tool, check
the results, and refine.

### 10.1 What are the limitations or biases in your system?

The Module 1–3 biases still apply and are now *inherited* by the AI layer, because the
agent scores through the same engine: **genre dominance** (genre is the heaviest weight,
so "right genre / wrong mood" beats "wrong genre / perfect mood"), a **tiny 18-song
catalog** (most genres have 1–3 tracks, so results are bounded by what exists), and **no
listening history or collaborative signal**. The agentic layer adds its own limitations:

- **The AI can only be as good as the engine and catalog.** Claude can reason about a
  request, but it cannot conjure a better-matching song that isn't in the CSV — it can
  only pick the closest available profile.
- **Language → profile mapping carries the model's own biases.** When Claude (or the
  keyword fallback) maps a phrase like *"moody"* or *"chill"* to a specific genre/mood, it
  is applying assumptions from its training about what those words mean — assumptions that
  are cultural and contestable, not neutral facts about music.
- **Non-determinism.** The same request can produce slightly different profiles or
  phrasing across runs, which makes the AI path harder to test and less predictable than
  the pure engine.
- **External dependency.** The agentic path needs an API key, network, cost, and latency;
  the fallback keeps the system *available* but at clearly lower quality.

### 10.2 Could your AI be misused, and how would you prevent that?

The main misuse risk is **overtrust** — presenting VibeFinder as if it "understands" a
listener's taste. It will confidently return a top 5 for a contradictory or impossible
request (e.g. `sad + high-energy metal`, or a genre absent from the catalog), and a
polished natural-language summary from the AI can make a weak, toy-catalog result *sound*
authoritative. At scale, the designer's weight choices (genre = 2.0) would get presented
to users as if they were objective truths about music. Preventions built into the system:

- **The engine is the only thing that scores.** Claude is restricted to *calling* the
  scoring tool — it can never invent songs, artists, or numbers, so every claim traces
  back to an auditable score.
- **Transparency by default.** Every recommendation ships with a per-feature *"Because…"*
  breakdown, so a user (or reviewer) can see exactly why a song ranked where it did.
- **Guardrails.** Model-produced profiles are validated and clamped, the agent loop is
  capped (`MAX_STEPS`), and errors degrade to the fallback instead of failing silently.
- **Honest scoping.** The "Not intended for" section and documented limitations make clear
  this is a teaching tool over 18 songs, not a product.
- **Human-in-the-loop.** The listener reviews and accepts/rejects the final result.

For a real deployment I would also add explicit contradiction detection and a "no good
match found" signal, so the system communicates uncertainty instead of masking it.

### 10.3 What surprised you while testing your AI's reliability?

The most surprising thing was that **the least reliable part of the system was not the
LLM — it was the "safe" deterministic fallback I wrote as a backup.** When I tested
*"calm ambient music to fall asleep to"* with no API key, the keyword parser had no mood
word to match, so it silently defaulted to the **alphabetically-first** mood in the
catalog — *"aggressive"* — and confidently recommended a **metal** track (*Broken Mirror*)
for a sleep playlist. I had assumed the risky, unpredictable component would be the AI and
that the hand-written code was the trustworthy floor; it was the opposite. The failure was
*silent and confident*, which is exactly the failure mode that's hardest to catch — it
only surfaced because I fed the system an input the happy-path tests never covered. I
fixed the parser to leave genre/mood blank when nothing matches, and the same request now
returns calm ambient tracks.

### 10.4 Collaboration with AI: one helpful suggestion and one flawed suggestion

I built VibeFinder 2.0 with an AI coding assistant (Claude Code), which was genuinely
useful for scaffolding and iterating quickly — but it also required real oversight.

**One helpful suggestion.** When I asked which advanced feature to add, the assistant
recommended an *agentic workflow that exposes the existing scoring engine to the model as
a tool*, rather than letting the LLM generate recommendations directly. This turned out to
be the backbone of the whole design: because the model can only *call* the deterministic
engine, the system stays fully auditable and can't hallucinate songs or scores. It was the
right architectural call and made the AI feature both easier to trust and easier to test.

**One flawed suggestion.** The same assistant wrote the keyword fallback, and its code
defaulted an unmatched mood to the alphabetically-first mood (`"aggressive"`). It read as
perfectly reasonable in review — but it produced the "aggressive metal for a sleep
playlist" bug in Section 10.3. I only caught it by *running* an edge-case input, not by
reading the code. The lesson mirrors what I learned in Module 1–3 (an AI-suggested import
that silently failed under `python -m src.main`): AI-generated code is often
plausible-but-wrong in exactly the spots you don't think to test, so it has to be executed
against adversarial inputs, not just accepted because it looks correct.
