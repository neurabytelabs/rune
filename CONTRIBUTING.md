# Contributing to Master Prompt

Thank you for your interest in contributing! 🎉

## How to Contribute

1. **Fork** the repository
2. **Create a branch** (`git checkout -b feature/my-feature`)
3. **Make your changes** and commit (`git commit -m "Add: my feature"`)
4. **Push** to your fork (`git push origin feature/my-feature`)
5. **Open a Pull Request** against `main`

## Adding a New Prompt

The prompt library lives in `prompts/`. To add a new prompt:

1. Create `prompts/NN_your_prompt.md` (next available number)
2. Follow this structure:
   ```markdown
   # 🎯 Prompt Title
   
   Brief description of what this prompt does.
   
   ## Kullanım / Usage
   
   When to use this prompt.
   
   ## Template
   
   ```xml
   <system>
     <!-- L1–L7 layers as needed -->
   </system>
   ```
   
   ## Example
   
   Show an example input and expected output.
   ```
3. Use the 8-layer XML structure from [MP v4.4](Master%20Prompt%20Template%20v4.4.md)
4. Test with at least 2 models using `cross_model_test.py`
5. Add your prompt to the table in the main README

## Modifying the Template

The core template (`Master Prompt Template v4.x.md`) is the heart of this project. Changes should:

- Preserve backward compatibility with existing prompts
- Include rationale in the PR description
- Be tested across multiple models
- Update the version number appropriately

## Issue Templates

- 🐛 **Bug Report** — Something isn't working
- 💡 **Feature Request** — Suggest an improvement
- 📝 **New Prompt** — Propose a prompt for the library

## Code of Conduct

Be kind, be constructive, be respectful. We're all here to make better prompts.

## Questions?

Open an issue or reach out on [Twitter @00xmorty](https://twitter.com/00xmorty).
