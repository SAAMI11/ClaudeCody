"""
plugin_loader.py
=================
Minimal plugin system for SAAMai. Any file dropped into
``backend/app/plugins/`` that defines a subclass of :class:`SAAMaiPlugin`
is auto-discovered on startup - no registration step needed.

Plugins can hook into two points:
  - ``before_prompt(text, context)``  - inspect/modify the user's message
    before it is sent to the model (e.g. add extra instructions).
  - ``after_response(text, context)`` - inspect/modify the model's reply
    before it is stored and sent to the client.

This keeps the extension surface small and safe on purpose: plugins run
in-process (no arbitrary network access is granted by the loader itself)
and simply transform text, which covers most real use cases (custom
system prompts, redaction, formatting, logging, simple tool calls) while
staying easy to audit.
"""

import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field

from .. import plugins as plugins_package


@dataclass
class PluginContext:
    chat_id: int
    user_id: int
    extra: dict = field(default_factory=dict)


class SAAMaiPlugin:
    """Base class every plugin must inherit from."""

    name: str = "unnamed-plugin"
    description: str = ""

    def before_prompt(self, text: str, context: PluginContext) -> str:
        return text

    def after_response(self, text: str, context: PluginContext) -> str:
        return text


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: list[SAAMaiPlugin] = []

    def discover(self) -> None:
        self._plugins.clear()
        for _, module_name, _ in pkgutil.iter_modules(plugins_package.__path__):
            module = importlib.import_module(f"{plugins_package.__name__}.{module_name}")
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, SAAMaiPlugin) and obj is not SAAMaiPlugin:
                    self._plugins.append(obj())

    @property
    def plugins(self) -> list[SAAMaiPlugin]:
        return self._plugins

    def run_before_prompt(self, text: str, context: PluginContext) -> str:
        for plugin in self._plugins:
            text = plugin.before_prompt(text, context)
        return text

    def run_after_response(self, text: str, context: PluginContext) -> str:
        for plugin in self._plugins:
            text = plugin.after_response(text, context)
        return text


registry = PluginRegistry()
