"""
⚙️ RUNE Settings — Configuration Management
TOML-based config with sensible defaults.
"""
import os
import copy
from typing import Any, Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]


DEFAULTS: dict[str, Any] = {
    "general": {
        "version": "1.0.0",
        "template_version": "v4.3",
        "color": True,
        "verbose": False,
        "locale": "auto",
    },
    "llm": {
        "api_url": "http://127.0.0.1:8045/v1/chat/completions",
        "api_key": "sk-f741397b2b564a1eaac8e714034eec2f",
        "default_model": "gemini-3-pro",
        "timeout": 120,
        "max_tokens": 8000,
        "temperature": 0.7,
        "stream": False,
    },
    "spinoza": {
        "enabled": True,
        "threshold": 0.6,
        "weights": {
            "conatus": 0.30,
            "ratio": 0.35,
            "laetitia": 0.15,
            "natura": 0.20,
        },
    },
    "paths": {
        "output_dir": "outputs",
        "prompts_dir": "prompts",
        "templates_dir": "templates",
        "db_path": "~/.rune/history.db",
    },
}


def _toml_value(v: Any) -> str:
    """Serialize a Python value to TOML literal."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(v)
    if isinstance(v, str):
        return f'"{v}"'
    raise TypeError(f"Unsupported TOML type: {type(v)}")


def _write_toml(data: dict[str, Any], path: str) -> None:
    """Write a nested dict as TOML (max 2 levels of nesting)."""
    lines: list[str] = []
    for section, values in data.items():
        if not isinstance(values, dict):
            continue
        # Check for sub-tables
        simple: dict[str, Any] = {}
        nested: dict[str, dict[str, Any]] = {}
        for k, v in values.items():
            if isinstance(v, dict):
                nested[k] = v
            else:
                simple[k] = v

        if simple:
            lines.append(f"[{section}]")
            for k, v in simple.items():
                lines.append(f"{k} = {_toml_value(v)}")
            lines.append("")

        for sub_name, sub_values in nested.items():
            lines.append(f"[{section}.{sub_name}]")
            for k, v in sub_values.items():
                lines.append(f"{k} = {_toml_value(v)}")
            lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


class Settings:
    """TOML-based configuration with sensible defaults."""

    def __init__(self, config_path: str = "~/.rune/config.toml") -> None:
        self.config_path = os.path.expanduser(config_path)
        self._data: dict[str, Any] = copy.deepcopy(DEFAULTS)
        if os.path.exists(self.config_path):
            self.load()

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a config value by section and key."""
        return self._data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        """Set a config value and persist to disk."""
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value
        self.save()

    def save(self) -> None:
        """Write current config to TOML file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        _write_toml(self._data, self.config_path)

    def load(self) -> None:
        """Read config from TOML file, merging over defaults."""
        if tomllib is None:
            return  # silently use defaults if no tomllib
        try:
            with open(self.config_path, "rb") as f:
                file_data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError):
            return
        # Deep merge: file values override defaults
        for section, values in file_data.items():
            if isinstance(values, dict):
                if section not in self._data:
                    self._data[section] = {}
                for k, v in values.items():
                    if isinstance(v, dict) and isinstance(self._data[section].get(k), dict):
                        self._data[section][k].update(v)
                    else:
                        self._data[section][k] = v

    def create_default_config(self) -> str:
        """Create ~/.rune/ directory and default config.toml. Returns path."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        self._data = copy.deepcopy(DEFAULTS)
        self.save()
        return self.config_path

    def format_config(self) -> str:
        """Display current configuration nicely."""
        lines = [
            "╔══════════════════════════════════════════╗",
            "║         ⚙️  RUNE Configuration            ║",
            "╠══════════════════════════════════════════╣",
        ]
        for section, values in self._data.items():
            lines.append(f"║  [{section}]")
            if isinstance(values, dict):
                for k, v in values.items():
                    if isinstance(v, dict):
                        lines.append(f"║    [{k}]")
                        for sk, sv in v.items():
                            lines.append(f"║      {sk} = {sv}")
                    else:
                        display = v
                        if k == "api_key" and isinstance(v, str) and len(v) > 8:
                            display = v[:8] + "…"
                        lines.append(f"║    {k} = {display}")
            lines.append("║")
        lines.append("╚══════════════════════════════════════════╝")
        return "\n".join(lines)
