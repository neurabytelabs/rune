"""
📜 RUNE Enhancer — The 8-Layer Prompt Transmutation Engine
Transforms simple prompts into powerful, structured LLM instructions.

Each prompt passes through 8 archetypal layers (runes), gaining structure,
safety, reasoning transparency, and output control. The result is a fully
specified XML prompt ready for any frontier LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Layer:
    """One of the 8 rune layers that compose a master prompt."""

    index: int
    name: str
    description: str
    xml_tag: str

    def __str__(self) -> str:
        return f"Layer {self.index}: {self.name}"


LAYERS: list[Layer] = [
    Layer(0, "System Core",
          "Prime directive, mode, temporal anchor",
          "layer_0_system_core"),
    Layer(1, "Context & Identity",
          "Persona, expertise, cultural competence",
          "layer_1_context_and_identity"),
    Layer(2, "Intent & Scope",
          "Objective, disambiguation, knowledge boundary",
          "layer_2_intent_and_scope"),
    Layer(3, "Governance & Safety",
          "Guardrails, error taxonomy, constraints",
          "layer_3_governance_and_safety"),
    Layer(4, "Cognitive Engine",
          "Reasoning transparency, collaborative intelligence",
          "layer_4_cognitive_engine"),
    Layer(5, "Capabilities",
          "Tool orchestration, memory protocol",
          "layer_5_capabilities"),
    Layer(6, "Quality Assurance",
          "Validation loop, self-correction, scoring",
          "layer_6_quality_assurance"),
    Layer(7, "Output & Meta",
          "Format enforcement, metadata, testing hook",
          "layer_7_output_and_meta"),
]


@dataclass
class EnhancedPrompt:
    """The output of the enhancement pipeline."""

    original: str
    enhanced: str                       # Full XML-structured prompt
    layers_applied: list[str]
    context: dict
    template_version: str
    timestamp: str
    estimated_tokens: int               # Rough estimate (chars / 4)

    def __str__(self) -> str:
        return self.enhanced


# ---------------------------------------------------------------------------
# Complexity classification
# ---------------------------------------------------------------------------

_COMPLEXITY_KEYWORDS: dict[str, list[str]] = {
    "L4": ["architect", "design system", "multi-agent", "pipeline", "orchestrat",
            "framework", "full-stack", "end-to-end", "microservice"],
    "L3": ["refactor", "optimize", "integrate", "migrate", "analyz", "compar",
            "review", "debug", "evaluate"],
    "L2": ["implement", "create", "build", "write", "generate", "convert",
            "translate", "explain"],
    "L1": ["list", "summarize", "define", "what is", "hello", "thanks"],
}


def _classify_complexity(prompt: str) -> str:
    """Return L1-L4 complexity tag based on keyword heuristics."""
    lower = prompt.lower()
    for level in ("L4", "L3", "L2", "L1"):
        if any(kw in lower for kw in _COMPLEXITY_KEYWORDS[level]):
            return level
    return "L2"  # sensible default


def _layers_for_complexity(level: str) -> list[Layer]:
    """Return which layers are relevant for a complexity level."""
    if level == "L1":
        return [LAYERS[0], LAYERS[2], LAYERS[7]]
    if level == "L2":
        return [LAYERS[0], LAYERS[1], LAYERS[2], LAYERS[3], LAYERS[7]]
    if level == "L3":
        return [LAYERS[i] for i in (0, 1, 2, 3, 4, 6, 7)]
    # L4 — all layers
    return list(LAYERS)


# ---------------------------------------------------------------------------
# Meta-prompt (the RUNE Architect instruction)
# ---------------------------------------------------------------------------

_META_PROMPT_TR = """\
Sen "RUNE Architect v1.0"sün. Görevin: kullanıcının basit isteğini alıp
RUNE Framework'ün 8 katmanlı yapısına uygun bir prompt üretmek.

KURALLAR:
1. v4.3 XML yapısını koru (<master_prompt_v4.3> wrapper).
2. Belirsiz alanları [EKSİK: ...] olarak işaretle.
3. Görev karmaşıklığını L1-L4 sınıfla, gereksiz katmanları atla.
4. Collaborative Intelligence gerekiyorsa hangi alt-ajanlar çağrılacağını belirt.
5. Error Taxonomy'den olası hata türlerini önceden tahmin et.
6. Sadece promptu ver, açıklama ekleme.
7. Kullanıcı Türkçe yazdıysa Türkçe, İngilizce yazdıysa İngilizce.

GİRDİ: {{USER_PROMPT}}"""

_META_PROMPT_EN = """\
You are "RUNE Architect v1.0". Your task: take the user's simple request and
produce a prompt that conforms to RUNE Framework's 8-layer structure.

RULES:
1. Preserve the v4.3 XML structure (<master_prompt_v4.3> wrapper).
2. Mark ambiguous fields as [MISSING: ...].
3. Classify task complexity L1-L4; skip unnecessary layers.
4. If Collaborative Intelligence is needed, specify which sub-agents to invoke.
5. Predict likely error types from the Error Taxonomy.
6. Output only the prompt — no explanations.
7. Match the user's language (Turkish → Turkish, English → English).

INPUT: {{USER_PROMPT}}"""


# ---------------------------------------------------------------------------
# Layer content generators
# ---------------------------------------------------------------------------

def _render_layer_0(prompt: str, ctx: dict) -> str:
    locale = ctx.get("locale", "en")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"  <layer_0_system_core>\n"
        f"    <role>Expert AI Assistant</role>\n"
        f"    <mode>structured_response</mode>\n"
        f"    <locale>{locale}</locale>\n"
        f"    <temporal_anchor>{now}</temporal_anchor>\n"
        f"  </layer_0_system_core>"
    )


def _render_layer_1(prompt: str, ctx: dict) -> str:
    domain = ctx.get("domain", "[EKSİK: domain]")
    level = ctx.get("expertise_level", "intermediate")
    return (
        f"  <layer_1_context_and_identity>\n"
        f"    <domain>{domain}</domain>\n"
        f"    <expertise_level>{level}</expertise_level>\n"
        f"    <cultural_competence>{ctx.get('locale', 'en')}</cultural_competence>\n"
        f"  </layer_1_context_and_identity>"
    )


def _render_layer_2(prompt: str, ctx: dict) -> str:
    return (
        f"  <layer_2_intent_and_scope>\n"
        f"    <objective>{prompt}</objective>\n"
        f"    <disambiguation>If ambiguous, ask one clarifying question.</disambiguation>\n"
        f"    <knowledge_boundary>Up to training cutoff + provided context.</knowledge_boundary>\n"
        f"  </layer_2_intent_and_scope>"
    )


def _render_layer_3(prompt: str, ctx: dict) -> str:
    constraints = ctx.get("constraints", "none")
    return (
        f"  <layer_3_governance_and_safety>\n"
        f"    <guardrails>No harmful content. Respect copyright.</guardrails>\n"
        f"    <error_taxonomy>hallucination, scope_creep, ambiguity</error_taxonomy>\n"
        f"    <constraints>{constraints}</constraints>\n"
        f"  </layer_3_governance_and_safety>"
    )


def _render_layer_4(prompt: str, ctx: dict) -> str:
    return (
        "  <layer_4_cognitive_engine>\n"
        "    <reasoning>Show step-by-step reasoning when complexity ≥ L3.</reasoning>\n"
        "    <collaborative_intelligence>Invoke sub-agents if task is multi-domain.</collaborative_intelligence>\n"
        "  </layer_4_cognitive_engine>"
    )


def _render_layer_5(prompt: str, ctx: dict) -> str:
    return (
        "  <layer_5_capabilities>\n"
        "    <tool_orchestration>Use available tools as needed.</tool_orchestration>\n"
        "    <memory_protocol>Reference prior context when available.</memory_protocol>\n"
        "  </layer_5_capabilities>"
    )


def _render_layer_6(prompt: str, ctx: dict) -> str:
    return (
        "  <layer_6_quality_assurance>\n"
        "    <validation>Self-check output against objective before responding.</validation>\n"
        "    <self_correction>If error detected, revise inline.</self_correction>\n"
        "    <quality_score>Rate confidence 1-10 at the end.</quality_score>\n"
        "  </layer_6_quality_assurance>"
    )


def _render_layer_7(prompt: str, ctx: dict) -> str:
    fmt = ctx.get("output_format", "markdown")
    return (
        f"  <layer_7_output_and_meta>\n"
        f"    <format>{fmt}</format>\n"
        f"    <metadata>template_version=v4.3</metadata>\n"
        f"    <testing_hook>DRY_RUN=false</testing_hook>\n"
        f"  </layer_7_output_and_meta>"
    )


_LAYER_RENDERERS = {
    0: _render_layer_0,
    1: _render_layer_1,
    2: _render_layer_2,
    3: _render_layer_3,
    4: _render_layer_4,
    5: _render_layer_5,
    6: _render_layer_6,
    7: _render_layer_7,
}


# ---------------------------------------------------------------------------
# Enhancer
# ---------------------------------------------------------------------------

class Enhancer:
    """The 8-layer prompt transmutation engine.

    Usage::

        enhancer = Enhancer()
        result = enhancer.enhance("Write a Python REST API for todo items")
        print(result.enhanced)

    The enhancer wraps any simple prompt in the RUNE v4.3 XML structure,
    selecting which layers to include based on task complexity (L1-L4).
    """

    def __init__(self, template_version: str = "v4.3") -> None:
        self.template_version = template_version
        self.layers = self._load_layers()

    # -- public API ---------------------------------------------------------

    def enhance(self, prompt: str, context: Optional[dict] = None) -> EnhancedPrompt:
        """Apply rune layers to transform a simple prompt.

        Args:
            prompt: The raw user prompt.
            context: Optional dict with keys like *domain*, *expertise_level*,
                     *output_format*, *constraints*, *locale*.

        Returns:
            An ``EnhancedPrompt`` with the full XML-structured output.
        """
        ctx = context or {}
        complexity = _classify_complexity(prompt)
        active_layers = _layers_for_complexity(complexity)

        xml_parts: list[str] = [f'<master_prompt_v4.3 complexity="{complexity}">']
        applied: list[str] = []

        for layer in active_layers:
            renderer = _LAYER_RENDERERS.get(layer.index)
            if renderer:
                xml_parts.append(renderer(prompt, ctx))
                applied.append(layer.name)

        xml_parts.append("</master_prompt_v4.3>")
        enhanced_text = "\n".join(xml_parts)

        return EnhancedPrompt(
            original=prompt,
            enhanced=enhanced_text,
            layers_applied=applied,
            context=ctx,
            template_version=self.template_version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            estimated_tokens=len(enhanced_text) // 4,
        )

    def enhance_with_rune(self, prompt: str, rune_name: str) -> EnhancedPrompt:
        """Apply a named rune template from the grimoire.

        Currently maps rune names to domain-specific context presets.
        Extend the ``_RUNE_PRESETS`` dict to add custom rune templates.

        Args:
            prompt: The raw user prompt.
            rune_name: A preset name such as ``"code"``, ``"creative"``,
                       ``"analysis"``, or ``"general"``.

        Returns:
            An ``EnhancedPrompt``.
        """
        preset = _RUNE_PRESETS.get(rune_name, {})
        return self.enhance(prompt, context=preset)

    def get_meta_prompt(self, locale: str = "tr") -> str:
        """Return the meta-prompt that instructs an LLM to enhance prompts.

        Args:
            locale: ``"tr"`` for Turkish (default) or ``"en"`` for English.

        Returns:
            The full RUNE Architect system prompt as a string.
        """
        return _META_PROMPT_TR if locale == "tr" else _META_PROMPT_EN

    def format_enhanced(self, result: EnhancedPrompt, verbose: bool = False) -> str:
        """Pretty-format an ``EnhancedPrompt`` for display.

        Args:
            result: The enhanced prompt to format.
            verbose: If *True*, include metadata header.

        Returns:
            A human-readable string.
        """
        parts: list[str] = []
        if verbose:
            parts.append(f"── RUNE Enhanced Prompt ──")
            parts.append(f"Template : {result.template_version}")
            parts.append(f"Layers   : {', '.join(result.layers_applied)}")
            parts.append(f"Tokens   : ~{result.estimated_tokens}")
            parts.append(f"Time     : {result.timestamp}")
            parts.append("─" * 40)
        parts.append(result.enhanced)
        return "\n".join(parts)

    # -- private ------------------------------------------------------------

    @staticmethod
    def _load_layers() -> list[Layer]:
        """Return the canonical 8 RUNE layers."""
        return list(LAYERS)


# ---------------------------------------------------------------------------
# Rune presets (grimoire entries)
# ---------------------------------------------------------------------------

_RUNE_PRESETS: dict[str, dict] = {
    "code": {
        "domain": "software_engineering",
        "expertise_level": "senior",
        "output_format": "code",
        "locale": "en",
    },
    "creative": {
        "domain": "creative_writing",
        "expertise_level": "expert",
        "output_format": "prose",
        "locale": "en",
    },
    "analysis": {
        "domain": "data_analysis",
        "expertise_level": "senior",
        "output_format": "markdown",
        "locale": "en",
    },
    "turkish": {
        "domain": "genel",
        "expertise_level": "uzman",
        "output_format": "markdown",
        "locale": "tr",
    },
    "general": {
        "domain": "general",
        "expertise_level": "intermediate",
        "output_format": "markdown",
        "locale": "en",
    },
}


# ---------------------------------------------------------------------------
# Quick CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    e = Enhancer()
    result = e.enhance(
        "Build a REST API for a todo app with authentication",
        context={"domain": "backend", "locale": "en"},
    )
    print(e.format_enhanced(result, verbose=True))
