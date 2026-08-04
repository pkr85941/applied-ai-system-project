"""
VibeFinder 2.0 — Agentic recommendation layer.

This module wraps the deterministic recommender in `recommender.py` with an
agentic AI workflow powered by Claude. The agent turns a free-text request like
"something moody for a late-night drive" into a structured taste profile, then:

    PLAN  → decide a taste profile from the natural-language request
    ACT   → call the deterministic `recommend_songs` engine as a tool
    CHECK → inspect the scores / genre match to judge whether the results are good
    REFINE→ adjust the profile and try again when the catalog didn't match well

The rule-based scoring engine stays the trustworthy core — Claude never invents
songs or scores, it only decides *what to ask the engine for* and *whether the
answer is good enough*. If no Anthropic credentials are available (or the SDK is
not installed), the module falls back to a deterministic keyword parser so the
project still runs reproducibly without secrets.

Run it:

    python -m src.agent "chill lofi for studying, I like acoustic"

Configure the model with the VIBEFINDER_MODEL env var (defaults to claude-opus-5).
"""

import json
import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

from src.recommender import load_songs, recommend_songs

# --- Configuration -----------------------------------------------------------

MODEL = os.getenv("VIBEFINDER_MODEL", "claude-opus-5")
DATA_PATH = os.getenv("VIBEFINDER_DATA", "data/songs.csv")
MAX_STEPS = 6  # guardrail: cap agent loop iterations so it can never spin forever
MAX_TOKENS = 4096


# --- Logging (tracks every plan / act / check step) --------------------------

def _build_logger() -> logging.Logger:
    """Configures a logger that writes to stderr and to logs/agent_run.log."""
    logger = logging.getLogger("vibefinder.agent")
    if logger.handlers:  # avoid duplicate handlers on re-import
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    try:
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler(os.path.join("logs", "agent_run.log"))
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        # If we can't write a log file (read-only fs, etc.) keep going with stderr.
        pass

    return logger


log = _build_logger()


# --- Catalog helpers ---------------------------------------------------------

def catalog_summary(songs: List[Dict]) -> Dict:
    """Summarizes the catalog so the agent can judge what it can realistically ask for."""
    genres = sorted({s["genre"] for s in songs})
    moods = sorted({s["mood"] for s in songs})
    energies = [s["energy"] for s in songs]
    return {
        "song_count": len(songs),
        "genres": genres,
        "moods": moods,
        "energy_min": round(min(energies), 2) if energies else None,
        "energy_max": round(max(energies), 2) if energies else None,
    }


# --- Tools exposed to Claude -------------------------------------------------

TOOLS = [
    {
        "name": "get_catalog_summary",
        "description": (
            "Return the list of genres and moods that actually exist in the song "
            "catalog, plus the number of songs and the energy range. Call this first "
            "so you request a profile the catalog can actually satisfy."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "recommend_songs",
        "description": (
            "Score every song in the catalog against a taste profile and return the "
            "top matches with their numeric score and a per-feature explanation. This "
            "is the trustworthy scoring engine — use it to actually generate "
            "recommendations. Inspect the returned scores: a low top score or no genre "
            "match means the profile fits the catalog poorly, so consider calling again "
            "with a relaxed profile."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "favorite_genre": {"type": "string", "description": "Preferred genre, e.g. 'lofi'."},
                "favorite_mood": {"type": "string", "description": "Preferred mood, e.g. 'chill'."},
                "target_energy": {
                    "type": "number",
                    "description": "Desired energy 0.0 (calm) to 1.0 (hyped).",
                },
                "likes_acoustic": {
                    "type": "boolean",
                    "description": "Whether the listener likes acoustic songs.",
                },
                "k": {"type": "integer", "description": "How many recommendations to return (default 5)."},
            },
            "required": ["favorite_genre", "favorite_mood", "target_energy", "likes_acoustic"],
        },
    },
]


def _validate_profile(tool_input: Dict) -> Dict:
    """Guardrail: coerce/validate the profile the model produced before scoring."""
    energy = tool_input.get("target_energy", 0.5)
    try:
        energy = float(energy)
    except (TypeError, ValueError):
        energy = 0.5
    energy = max(0.0, min(1.0, energy))  # clamp into [0, 1]

    k = tool_input.get("k", 5)
    try:
        k = int(k)
    except (TypeError, ValueError):
        k = 5
    k = max(1, min(10, k))

    return {
        "genre": str(tool_input.get("favorite_genre", "")).strip().lower(),
        "mood": str(tool_input.get("favorite_mood", "")).strip().lower(),
        "energy": energy,
        "likes_acoustic": bool(tool_input.get("likes_acoustic", False)),
        "k": k,
    }


def _execute_tool(name: str, tool_input: Dict, songs: List[Dict]) -> str:
    """Runs one tool call and returns a JSON string for the tool_result block."""
    if name == "get_catalog_summary":
        log.info("ACT  get_catalog_summary()")
        return json.dumps(catalog_summary(songs))

    if name == "recommend_songs":
        profile = _validate_profile(tool_input)
        log.info("ACT  recommend_songs(profile=%s)", profile)
        ranked = recommend_songs(profile, songs, k=profile["k"])
        results = [
            {
                "title": song["title"],
                "artist": song["artist"],
                "genre": song["genre"],
                "mood": song["mood"],
                "score": round(score, 2),
                "explanation": explanation,
            }
            for song, score, explanation in ranked
        ]
        top = results[0]["score"] if results else None
        log.info("CHECK top score=%s across %d results", top, len(results))
        return json.dumps({"profile_used": profile, "results": results})

    log.warning("Unknown tool requested: %s", name)
    return json.dumps({"error": f"unknown tool '{name}'"})


SYSTEM_PROMPT = (
    "You are VibeFinder, a music-recommendation agent working over a small fixed "
    "song catalog. A listener describes what they want in plain language. Your job:\n"
    "1. PLAN: call get_catalog_summary so you only request genres/moods that exist.\n"
    "2. ACT: translate the request into a taste profile and call recommend_songs.\n"
    "3. CHECK: read the returned scores. If the top score is weak or nothing matches "
    "the requested genre, the catalog is a poor fit — REFINE the profile (e.g. relax "
    "the genre to the closest available one, or adjust energy) and call again.\n"
    "4. Then give the listener a short, friendly recommendation: name the top picks "
    "and briefly say why, grounded in the engine's explanations. Never invent songs, "
    "artists, or scores — only report what recommend_songs returned. Keep it concise."
)


# --- Deterministic fallback (no credentials required) ------------------------

def _keyword_profile(request: str, songs: List[Dict]) -> Dict:
    """Maps free text to a taste profile using catalog vocabulary — no LLM needed."""
    text = request.lower()
    summary = catalog_summary(songs)

    # Only assert a genre/mood the text actually mentions. Guessing a default here
    # (e.g. the alphabetically-first mood) would inject a misleading match — better
    # to leave it blank and let the engine award no points for that feature.
    genre = next((g for g in summary["genres"] if g in text), "")
    mood = next((m for m in summary["moods"] if m in text), "")

    # Energy cues.
    calm_words = ("chill", "calm", "relax", "sleep", "study", "mellow", "quiet", "soft")
    hype_words = ("hype", "energetic", "intense", "workout", "gym", "party", "pump", "hard")
    if any(w in text for w in hype_words):
        energy = 0.9
    elif any(w in text for w in calm_words):
        energy = 0.3
    else:
        energy = 0.5

    likes_acoustic = any(w in text for w in ("acoustic", "unplugged", "guitar"))
    return {"genre": genre, "mood": mood, "energy": energy, "likes_acoustic": likes_acoustic}


def _fallback(request: str, songs: List[Dict]) -> str:
    """Runs the deterministic path when Claude is unavailable."""
    log.info("Falling back to deterministic keyword recommender (no Claude credentials).")
    profile = _keyword_profile(request, songs)
    log.info("PLAN (fallback) profile=%s", profile)
    ranked = recommend_songs(profile, songs, k=5)
    lines = [f"(Deterministic fallback: no AI credentials found. Parsed profile: {profile})", ""]
    for rank, (song, score, explanation) in enumerate(ranked, start=1):
        lines.append(f"{rank}. {song['title']} by {song['artist']} - score {score:.2f}")
        lines.append(f"   Because: {explanation}")
    return "\n".join(lines)


# --- The agent loop ----------------------------------------------------------

def run_agent(request: str, songs: Optional[List[Dict]] = None) -> str:
    """
    Runs the agentic recommendation workflow for one natural-language request.

    Returns the agent's final recommendation text. Falls back to the deterministic
    keyword recommender if the Anthropic SDK or credentials are unavailable.
    """
    if songs is None:
        songs = load_songs(DATA_PATH)

    try:
        import anthropic
    except ImportError:
        log.warning("anthropic SDK not installed.")
        return _fallback(request, songs)

    try:
        client = anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY or an ant profile
    except Exception as exc:  # e.g. no credentials configured at all
        log.warning("Could not initialize Anthropic client: %s", exc)
        return _fallback(request, songs)

    messages: List[Dict] = [{"role": "user", "content": request}]
    log.info("PLAN start — request: %r (model=%s)", request, MODEL)

    try:
        for step in range(MAX_STEPS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                thinking={"type": "adaptive"},
                messages=messages,
            )

            if response.stop_reason == "refusal":
                log.warning("Model refused the request.")
                return "Sorry — I can't help with that request."

            # Preserve the full assistant turn (incl. thinking / tool_use blocks).
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = _execute_tool(block.name, block.input, songs)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )
                messages.append({"role": "user", "content": tool_results})
                continue

            # end_turn (or anything else terminal): return the final text.
            final = "".join(b.text for b in response.content if b.type == "text").strip()
            log.info("DONE after %d step(s).", step + 1)
            return final or "(No recommendation produced.)"

        log.warning("Hit MAX_STEPS (%d) without finishing.", MAX_STEPS)
        return "(Stopped: the agent took too many steps without finishing.)"

    except anthropic.AuthenticationError:
        log.warning("Authentication failed — no valid Anthropic credentials.")
        return _fallback(request, songs)
    except anthropic.APIConnectionError:
        log.warning("Could not reach the Anthropic API — using fallback.")
        return _fallback(request, songs)
    except anthropic.APIStatusError as exc:
        log.error("Anthropic API error (%s): %s", exc.status_code, exc.message)
        return _fallback(request, songs)


def main() -> None:
    """CLI entry point: python -m src.agent 'your vibe request here'."""
    if len(sys.argv) > 1:
        request = " ".join(sys.argv[1:])
    else:
        request = input("Describe the vibe you're after: ").strip()

    if not request:
        print("Please describe what you want to listen to.")
        return

    print(f"\n=== Request: {request} ===\n")
    print(run_agent(request))


if __name__ == "__main__":
    main()
