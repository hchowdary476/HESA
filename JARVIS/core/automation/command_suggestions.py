"""Context-aware command suggestions."""

from __future__ import annotations


def suggest_commands(context: dict) -> list[dict[str, str]]:
    """Suggest discoverable commands without proposing blocked destructive actions."""

    suggestions: list[dict[str, str]] = []
    
    # 1. Fetch suggestions from the learning engine
    try:
        from JARVIS.core.learning.learning_engine import PersonalLearningEngine
        engine = PersonalLearningEngine()
        learnt_suggestions = engine.generate_suggestions()
        for sug in learnt_suggestions:
            suggestions.append({
                "command": sug["command"],
                "category": sug["type"],
                "why": sug["why"]
            })
    except Exception:
        pass

    # 2. Append legacy status/fallback suggestions if queue is small
    if len(suggestions) < 3:
        missing = set(context.get("missing", []))
        if "spotify" in missing:
            suggestions.append({"command": "finish spotify setup", "category": "setup", "why": "Music commands need Spotify credentials."})
        if context.get("last_action") == "music":
            suggestions.append({"command": "play my favorite music", "category": "music", "why": "Your last interaction was music-focused."})
        suggestions.append({"command": "run health check", "category": "maintenance", "why": "Catch configuration issues early."})
        if context.get("permission_profile") != "safe":
            suggestions.append({"command": "lock the computer", "category": "runtime", "why": "Secure the current session quickly."})
            
    return suggestions
