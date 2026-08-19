"""Small, dependency-free hybrid-memory POC.

The in-memory adapter mirrors the production design: episodic memories are
retrieved with lexical + vector rank fusion, while profile and recent activity
are served as structured features.  Replace the adapter with Qdrant and Feast
when deploying the real system.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


TOPIC_KEYWORDS = {
    "cloud": {"cloud", "kubernetes", "k8s", "autoscaling", "hạ", "tầng"},
    "security": {"security", "bảo", "mật", "zero", "trust", "iam"},
    "ai_ml": {"ai", "ml", "model", "embedding", "llm", "vector"},
    "devops": {"docker", "ci", "cd", "pipeline", "deploy", "devops"},
}


@dataclass
class Memory:
    user_id: str
    text: str
    topic: str
    created_at: datetime
    vector: tuple[float, ...]


class HybridMemoryAgent:
    """Remember episodic text and assemble personalized recall context."""

    def __init__(self, dimensions: int = 96) -> None:
        self.dimensions = dimensions
        self.memories: list[Memory] = []
        self.activity: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
        self.profiles: dict[str, dict] = defaultdict(
            lambda: {
                "preferred_language": "vi/en mix",
                "reading_speed_wpm": 220,
                "topic_affinity": "cloud",
                "active_hours": "08:00-23:00",
                "topic_counts": Counter(),
            }
        )

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[\wÀ-ỹ]+", text.lower(), flags=re.UNICODE)

    def _embed(self, text: str) -> tuple[float, ...]:
        """Deterministic local vector; production uses a multilingual model."""
        values = [0.0] * self.dimensions
        for token in self._tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
            index = int.from_bytes(digest, "big") % self.dimensions
            values[index] += 1.0
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return tuple(v / norm for v in values)

    @staticmethod
    def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        return sum(a * b for a, b in zip(left, right))

    @staticmethod
    def _chunks(text: str, max_words: int = 80) -> list[str]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        chunks: list[str] = []
        current: list[str] = []
        for sentence in sentences or [text.strip()]:
            if len(" ".join(current + [sentence]).split()) > max_words and current:
                chunks.append(" ".join(current))
                current = []
            current.append(sentence)
        if current:
            chunks.append(" ".join(current))
        return chunks or [text.strip()]

    @staticmethod
    def _topic(text: str) -> str:
        tokens = set(HybridMemoryAgent._tokens(text))
        scores = {topic: len(tokens & words) for topic, words in TOPIC_KEYWORDS.items()}
        return max(scores, key=scores.get) if max(scores.values(), default=0) else "general"

    def _update_profile(self, user_id: str, text: str, topic: str) -> None:
        profile = self.profiles[user_id]
        counts: Counter = profile["topic_counts"]
        counts[topic] += 1
        profile["topic_affinity"] = counts.most_common(1)[0][0]
        english = sum(1 for token in self._tokens(text) if token.isascii())
        profile["preferred_language"] = "vi/en mix" if english else "vi"

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Add chunked episodic memory for one user."""
        now = datetime.now(timezone.utc)
        for chunk in self._chunks(text):
            topic = self._topic(chunk)
            self.memories.append(
                Memory(user_id, chunk, topic, now, self._embed(chunk))
            )
            self._update_profile(user_id, chunk, topic)

    def _recent(self, user_id: str, now: datetime) -> list[str]:
        cutoff = now - timedelta(hours=1)
        self.activity[user_id] = [(ts, q) for ts, q in self.activity[user_id] if ts >= cutoff]
        return [q for _, q in self.activity[user_id]]

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Return profile + recent activity + top-3 hybrid memories."""
        now = datetime.now(timezone.utc)
        self.activity[user_id].append((now, query))
        recent = self._recent(user_id, now)
        q_tokens = set(self._tokens(query))
        q_vector = self._embed(query)
        candidates = [m for m in self.memories if m.user_id == user_id]

        lexical = sorted(
            candidates,
            key=lambda m: len(q_tokens & set(self._tokens(m.text))),
            reverse=True,
        )
        semantic = sorted(candidates, key=lambda m: self._cosine(q_vector, m.vector), reverse=True)
        scores: dict[int, float] = {}
        for rank, memory in enumerate(lexical, start=1):
            scores[id(memory)] = scores.get(id(memory), 0.0) + 1 / (60 + rank)
        for rank, memory in enumerate(semantic, start=1):
            scores[id(memory)] = scores.get(id(memory), 0.0) + 1 / (60 + rank)
        top = sorted(candidates, key=lambda m: scores.get(id(m), 0.0), reverse=True)[:3]

        profile = self.profiles[user_id]
        recent_topics = Counter(self._topic(q) for q in recent)
        activity_text = "; ".join(recent[-3:]) if recent else "none"
        memories_text = " | ".join(f"[{m.topic}] {m.text}" for m in top) or "none"
        return (
            f"User profile: language={profile['preferred_language']}; "
            f"reading_speed={profile['reading_speed_wpm']}wpm; "
            f"topic_affinity={profile['topic_affinity']}; active={profile['active_hours']}\n"
            f"Recent activity ({len(recent)} in last hour): {activity_text}\n"
            f"Recent topics: {dict(recent_topics) or {}}\n"
            f"Top memories: {memories_text}"
        )
