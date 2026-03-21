"""
🐝 Swarm Orchestrator — Run multi-agent prompt evolution.
Unified with the RUNE provider system.
"""

from __future__ import annotations

import concurrent.futures
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rune.providers.base import LLMRequest
from rune.providers.openai_compat import OpenAICompatProvider
from rune.swarm.agents import STRATEGIES, AgentResult, DEFAULT_AGENT_TYPES, ALL_AGENT_TYPES
from rune.swarm.tournament import score_response


class SwarmOrchestrator:
    """Orchestrates multi-agent prompt evolution."""

    def __init__(self, provider: OpenAICompatProvider, model: str = "gemini-3-flash-preview"):
        self.provider = provider
        self.model = model

    def run_agent(self, agent_type: str, prompt: str, context: str = "") -> AgentResult:
        """Run a single agent."""
        strat = STRATEGIES[agent_type]
        system = strat["system"]
        if context:
            system += f"\n\nCONTEXT FROM OTHER AGENTS:\n{context}"

        try:
            request = LLMRequest(
                prompt=prompt,
                model=self.model,
                system=system,
                temperature=0.7,
                max_tokens=4000,
            )
            response = self.provider.call(request)
            text = response.content
            elapsed = response.elapsed_sec
            ti = response.tokens_in
            to = response.tokens_out
        except Exception as e:
            text = f"[ERROR: {e}]"
            elapsed, ti, to = 0, 0, 0

        scores = score_response(text)
        return AgentResult(
            agent_type=agent_type,
            name=strat["name"],
            emoji=strat["emoji"],
            system_prompt=system,
            response=text,
            scores=scores,
            overall=scores["overall"],
            time_sec=round(elapsed, 2),
            tokens_in=ti,
            tokens_out=to,
        )

    def fuse_responses(self, results: List[AgentResult], prompt: str) -> tuple[str, dict]:
        """Fuse top agent responses into a final synthesis."""
        fusion_system = (
            "You are the RUNE SWARM Synthesizer. You receive multiple expert responses "
            "to the same prompt, each from a different strategic angle. "
            "Your job: create the ULTIMATE response by combining the best elements.\n\n"
            "Rules:\n"
            "- Take the strongest insights from each agent\n"
            "- Resolve contradictions intelligently\n"
            "- The final output must be better than any individual response\n"
            "- Be concise — don't just concatenate, SYNTHESIZE\n"
            "- Structure for maximum clarity and impact"
        )

        agents_text = ""
        for r in results:
            agents_text += f"\n{'='*60}\n"
            agents_text += f"AGENT: {r.emoji} {r.name} (Score: {r.overall}/100)\n"
            agents_text += f"{'='*60}\n{r.response}\n"

        fusion_prompt = (
            f"ORIGINAL USER PROMPT:\n{prompt}\n\n"
            f"AGENT RESPONSES (ranked by Spinoza score):\n{agents_text}\n\n"
            "NOW: Create the definitive synthesis. Be better than any single agent."
        )

        try:
            request = LLMRequest(
                prompt=fusion_prompt,
                model=self.model,
                system=fusion_system,
                max_tokens=4000,
            )
            response = self.provider.call(request)
            scores = score_response(response.content)
            return response.content, scores
        except Exception as e:
            return f"[FUSION ERROR: {e}]", {"overall": 0}

    def swarm(
        self,
        prompt: str,
        agent_types: Optional[List[str]] = None,
        rounds: int = 1,
        top_k: int = 2,
    ) -> Dict:
        """Run the full SWARM pipeline. Returns report dict."""
        if agent_types is None:
            agent_types = DEFAULT_AGENT_TYPES

        all_results = []
        prev_context = ""

        for rnd in range(1, rounds + 1):
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(agent_types)) as executor:
                futures = {
                    executor.submit(self.run_agent, at, prompt, prev_context): at
                    for at in agent_types
                }
                for future in concurrent.futures.as_completed(futures):
                    r = future.result()
                    results.append(r)

            # Rank by score
            results.sort(key=lambda r: -r.overall)
            for i, r in enumerate(results, 1):
                r.rank = i

            all_results = results

            # Cross-pollination context for next round
            if rnd < rounds:
                top = results[:top_k]
                prev_context = "\n".join(
                    f"[{r.name} - Score {r.overall}]: {r.response[:500]}"
                    for r in top
                )

        # Fusion
        top = all_results[:top_k]
        fused_text, fused_scores = self.fuse_responses(top, prompt)
        best_agent_score = all_results[0].overall if all_results else 0

        # Build report
        report = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "model": self.model,
            "rounds": rounds,
            "agents": [
                {
                    "rank": r.rank,
                    "type": r.agent_type,
                    "name": r.name,
                    "scores": r.scores,
                    "overall": r.overall,
                    "time_sec": r.time_sec,
                    "tokens_out": r.tokens_out,
                    "response": r.response,
                }
                for r in all_results
            ],
            "fusion": {
                "text": fused_text,
                "scores": fused_scores,
                "improvement": round(
                    ((fused_scores.get("overall", 0) - best_agent_score) / best_agent_score * 100)
                    if best_agent_score > 0 else 0,
                    1,
                ),
            },
        }

        return report
