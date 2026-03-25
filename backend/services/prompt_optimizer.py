"""
Prompt Optimization Engine - Reduces token usage through prompt engineering
Uses NLP techniques to compress and optimize prompts
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger("backend.prompt_optimizer")


class PromptOptimizer:
    def __init__(self):
        self.stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "shall", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "under", "again",
            "further", "then", "once", "very", "really", "just", "please",
            "thank", "thanks", "kindly", "actually", "basically", "literally",
        }

    def optimize_prompt(
        self,
        prompt: str,
        strategy: str = "balanced",
        preserve_quality: bool = True,
    ) -> dict:
        original_tokens = self.estimate_tokens(prompt)
        optimizations = []

        if strategy == "aggressive":
            optimized, opts = self._aggressive_optimize(prompt)
        elif strategy == "conservative":
            optimized, opts = self._conservative_optimize(prompt)
        else:
            optimized, opts = self._balanced_optimize(prompt)

        optimizations.extend(opts)

        if preserve_quality:
            optimized = self._preserve_critical_content(optimized, prompt)

        optimized_tokens = self.estimate_tokens(optimized)
        savings = original_tokens - optimized_tokens
        savings_pct = (savings / original_tokens * 100) if original_tokens > 0 else 0

        return {
            "original": prompt,
            "optimized": optimized,
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "tokens_saved": savings,
            "savings_pct": round(savings_pct, 1),
            "optimizations_applied": optimizations,
            "strategy": strategy,
        }

    def _aggressive_optimize(self, prompt: str) -> tuple[str, list[str]]:
        opts = []
        result = prompt

        result, count = self._remove_filler_words(result)
        if count > 0:
            opts.append(f"removed_{count}_filler_words")

        result, count = self._remove_blank_lines(result)
        if count > 0:
            opts.append(f"removed_{count}_blank_lines")

        result = self._collapse_whitespace(result)
        opts.append("collapsed_whitespace")

        result, count = self._shorten_common_phrases(result)
        if count > 0:
            opts.append(f"shortened_{count}_phrases")

        result = self._remove_redundant_phrases(result)
        opts.append("removed_redundant_phrases")

        return result, opts

    def _balanced_optimize(self, prompt: str) -> tuple[str, list[str]]:
        opts = []
        result = prompt

        result, count = self._remove_blank_lines(result)
        if count > 0:
            opts.append(f"removed_{count}_blank_lines")

        result = self._collapse_whitespace(result)
        opts.append("collapsed_whitespace")

        result, count = self._shorten_common_phrases(result)
        if count > 0:
            opts.append(f"shortened_{count}_phrases")

        return result, opts

    def _conservative_optimize(self, prompt: str) -> tuple[str, list[str]]:
        opts = []
        result = prompt

        result, count = self._remove_blank_lines(result)
        if count > 0:
            opts.append(f"removed_{count}_blank_lines")

        result = self._collapse_whitespace(result)
        opts.append("collapsed_whitespace")

        return result, opts

    def _remove_filler_words(self, text: str) -> tuple[str, int]:
        words = text.split()
        count = 0
        filtered = []
        for word in words:
            lower = word.lower().strip(".,!?;:")
            if lower in self.stop_words and len(words) > 10:
                count += 1
            else:
                filtered.append(word)

        return " ".join(filtered), count

    def _remove_blank_lines(self, text: str) -> tuple[str, int]:
        lines = text.split("\n")
        original_count = len(lines)
        non_empty = [line for line in lines if line.strip()]
        removed = original_count - len(non_empty)
        return "\n".join(non_empty), removed

    def _collapse_whitespace(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def _shorten_common_phrases(self, text: str) -> tuple[str, int]:
        replacements = {
            "in order to": "to",
            "for the purpose of": "to",
            "with regard to": "regarding",
            "in spite of": "despite",
            "at this point in time": "now",
            "in the event that": "if",
            "due to the fact that": "because",
            "in spite of the fact that": "although",
            "it is important to note that": "",
            "it should be noted that": "",
            "as a matter of fact": "",
            "needless to say": "",
            "long story short": "",
            "the fact of the matter is": "",
            "what I mean to say is": "",
            "in other words": "",
            "as I mentioned before": "",
            "to make a long story short": "",
        }

        count = 0
        result = text
        for phrase, replacement in replacements.items():
            if phrase.lower() in result.lower():
                result = re.sub(re.escape(phrase), replacement, result, flags=re.IGNORECASE)
                count += 1

        return result, count

    def _remove_redundant_phrases(self, text: str) -> str:
        result = re.sub(r'(\b\w+\b)(\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)
        return result

    def _preserve_critical_content(self, optimized: str, original: str) -> str:
        code_blocks = re.findall(r'```[\s\S]*?```', original)
        for block in code_blocks:
            if block not in optimized:
                optimized = block + "\n" + optimized

        return optimized

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, len(text) // 4)

    def suggest_system_prompt_optimization(self, system_prompt: str) -> dict:
        suggestions = []
        token_count = self.estimate_tokens(system_prompt)

        if token_count > 1000:
            suggestions.append({
                "type": "LENGTH",
                "severity": "warning",
                "message": f"System prompt is {token_count} tokens. Consider shortening.",
                "suggestion": "Keep system prompts under 500 tokens for optimal performance.",
            })

        if len(system_prompt.split("\n")) > 20:
            suggestions.append({
                "type": "STRUCTURE",
                "severity": "info",
                "message": "System prompt has many lines. Consider using bullet points.",
            })

        if system_prompt.count("You are") > 1 or system_prompt.count("you are") > 1:
            suggestions.append({
                "type": "REDUNDANCY",
                "severity": "info",
                "message": "Multiple role definitions detected. Consolidate.",
            })

        return {
            "token_count": token_count,
            "suggestions": suggestions,
            "optimization_potential": "high" if token_count > 500 else "low",
        }

    def batch_optimize(self, prompts: list[str], strategy: str = "balanced") -> list[dict]:
        return [self.optimize_prompt(p, strategy) for p in prompts]
