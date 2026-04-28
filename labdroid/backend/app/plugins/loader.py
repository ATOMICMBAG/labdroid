from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

from app.plugins.base import InspectionPlugin


class PluginManager:
    def __init__(self, plugin_dir: Path) -> None:
        self.plugin_dir = plugin_dir
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: list[InspectionPlugin] = []

    def load_plugins(self) -> list[str]:
        self._plugins = []
        loaded_names: list[str] = []

        for path in sorted(self.plugin_dir.glob("*.py")):
            try:
                module = self._load_module(path)
                for obj in module.__dict__.values():
                    if isinstance(obj, type) and issubclass(obj, InspectionPlugin) and obj is not InspectionPlugin:
                        plugin = obj()
                        self._plugins.append(plugin)
                        loaded_names.append(plugin.name)
            except Exception:
                continue

        return loaded_names

    def run_all(self, input_data: dict) -> list[dict]:
        results: list[dict] = []
        for plugin in self._plugins:
            try:
                out = plugin.run(input_data)
                results.append({"plugin": plugin.name, "ok": True, "output": out})
            except Exception as exc:  # noqa: BLE001
                results.append({"plugin": plugin.name, "ok": False, "error": str(exc)})
        return results

    @property
    def plugins(self) -> list[str]:
        return [p.name for p in self._plugins]

    def _load_module(self, path: Path):
        module_name = f"labdroid_plugin_{path.stem}_{uuid.uuid4().hex[:8]}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            raise RuntimeError(f"cannot load spec for {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
