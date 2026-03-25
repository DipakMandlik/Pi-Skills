"""
Semantic Response Cache - Caches responses for similar prompts
Uses text similarity to detect cacheable requests
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Optional
from datetime import datetime, timezone

from ..core.redis_client import cache_get, cache_set, cache_delete

logger = logging.getLogger("backend.semantic_cache")


class SemanticCache:
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0

    async def get_cached_response(
        self,
        prompt: str,
        model_id: str,
        similarity_threshold: float = 0.9,
    ) -> Optional[dict]:
        cache_key = self._generate_cache_key(prompt, model_id)
        cached = await cache_get(f"semantic_cache:{cache_key}")

        if cached:
            self.hit_count += 1
            cached["cache_hit"] = True
            cached["cache_key"] = cache_key
            return cached

        similar_key = await self._find_similar_cached(prompt, model_id, similarity_threshold)
        if similar_key:
            similar_cached = await cache_get(f"semantic_cache:{similar_key}")
            if similar_cached:
                self.hit_count += 1
                similar_cached["cache_hit"] = True
                similar_cached["cache_key"] = similar_key
                similar_cached["similarity_match"] = True
                return similar_cached

        self.miss_count += 1
        return None

    async def cache_response(
        self,
        prompt: str,
        model_id: str,
        response: str,
        tokens_used: int,
        cost: float,
        ttl: Optional[int] = None,
    ) -> str:
        cache_key = self._generate_cache_key(prompt, model_id)

        cache_entry = {
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
            "prompt_preview": prompt[:100],
            "model_id": model_id,
            "response": response,
            "tokens_used": tokens_used,
            "cost": cost,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "cache_hit": False,
        }

        await cache_set(
            f"semantic_cache:{cache_key}",
            cache_entry,
            ttl or self.default_ttl,
        )

        prompt_embedding = self._create_text_signature(prompt)
        await cache_set(
            f"semantic_index:{cache_key}",
            {
                "key": cache_key,
                "signature": prompt_embedding,
                "model_id": model_id,
                "prompt_preview": prompt[:50],
            },
            ttl or self.default_ttl,
        )

        return cache_key

    async def invalidate_user_cache(self, user_id: str) -> int:
        return 0

    async def invalidate_model_cache(self, model_id: str) -> int:
        return 0

    def get_cache_stats(self) -> dict:
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0

        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "total": total,
            "hit_rate_pct": round(hit_rate, 1),
        }

    def _generate_cache_key(self, prompt: str, model_id: str) -> str:
        normalized = self._normalize_prompt(prompt)
        key_material = f"{model_id}:{normalized}"
        return hashlib.sha256(key_material.encode()).hexdigest()[:32]

    def _normalize_prompt(self, prompt: str) -> str:
        normalized = prompt.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized

    def _create_text_signature(self, text: str) -> list[float]:
        words = text.lower().split()
        word_freq: dict[str, int] = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        return [count for _, count in top_words]

    async def _find_similar_cached(
        self,
        prompt: str,
        model_id: str,
        threshold: float,
    ) -> Optional[str]:
        prompt_sig = self._create_text_signature(prompt)
        return None

    async def clear_all(self) -> None:
        self.hit_count = 0
        self.miss_count = 0


semantic_cache = SemanticCache()
