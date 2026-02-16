# 📂 Examples

## Showcase: OMNI-FLUX

[OMNI-FLUX](https://github.com/mrsarac/omni-flux) is a WebGL shader playground built entirely with Master Prompt-enhanced development. Every feature — from shader debugging to UI polish — was developed using MP prompts.

## Case Studies

### 🔮 Shader Debugging
**Problem:** Black screen on a fragment shader with 200+ lines of GLSL.
**Prompt used:** `01_shader_debug.md`
**Result:** Root cause identified in 1 response (uniform type mismatch), fix provided with explanation.

### 🗺️ Feature Planning
**Problem:** Needed to plan a roadmap for a multi-platform app with unclear priorities.
**Prompt used:** `04_feature_roadmap.md`
**Result:** Structured roadmap with phases, dependencies, and effort estimates. Saved ~2 days of planning.

### 🎨 UI Polish
**Problem:** Dashboard looked "functional but ugly" — needed design refinement.
**Prompt used:** `02_ui_polish.md`
**Result:** 12 specific, actionable UI improvements with CSS snippets. Implemented in 3 hours.

## Before & After

### Without Master Prompt:
```
"Fix my shader, it shows a black screen"
```
→ Generic debugging checklist, 50% chance of useful answer.

### With Master Prompt:
```xml
<system>
  <identity>Senior WebGL/GLSL engineer, 15+ years...</identity>
  <mission>Find root cause of shader failure...</mission>
  <constraints>Never modify working code outside bug scope...</constraints>
  <cognitive>Analyze: compile errors → uniforms → precision → logic...</cognitive>
  <qa>Verify fix compiles and renders correctly...</qa>
</system>
```
→ Targeted analysis, root cause in first response, minimal fix with explanation.

**The difference:** Structure turns a coin flip into a reliable outcome.
