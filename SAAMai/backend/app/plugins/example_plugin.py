"""
example_plugin.py
==================
Reference implementation showing how to write a SAAMai plugin. It logs
every prompt/response pair to the console without changing their
content, so the default install stays unmodified while still
demonstrating both hook points. Copy this file, rename the class, and
implement your own logic (e.g. redaction, custom system prompts, simple
tool calls) to build a real plugin.
"""

import logging

from ..services.plugin_loader import PluginContext, SAAMaiPlugin

logger = logging.getLogger("saamai.plugins.example")


class ExamplePlugin(SAAMaiPlugin):
    name = "example-plugin"
    description = "Demo-Plugin: protokolliert Prompts/Antworten, ohne sie zu veraendern."

    def before_prompt(self, text: str, context: PluginContext) -> str:
        logger.debug("chat=%s prompt: %s", context.chat_id, text[:200])
        return text

    def after_response(self, text: str, context: PluginContext) -> str:
        logger.debug("chat=%s response: %s", context.chat_id, text[:200])
        return text
