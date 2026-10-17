"""Round-trip edits of one client entry; never reserialize a JSONC document."""

from __future__ import annotations

import io
import json
import re
import math
from collections.abc import Mapping


class ConfigError(ValueError):
    pass


class JsonDocument:
    """JSON plus comments/trailing commas, with exact source spans for edits."""

    def __init__(self, text: str):
        if len(text) > 8 * 1024 * 1024:
            raise ConfigError("Client configuration exceeds the 8 MiB safety limit")
        self.text = text
        self.spans = {}
        self.members = {}
        self.position = 0
        self.value = self._value(())
        if self._space() != len(text) or not isinstance(self.value, dict):
            raise ConfigError("Client configuration must be one JSON object")

    def _space(self):
        while self.position < len(self.text):
            match = re.match(
                r"\s+|//[^\r\n]*|/\*[\s\S]*?\*/", self.text[self.position :]
            )
            if not match:
                break
            self.position += match.end()
        return self.position

    def _value(self, path):
        start = self._space()
        if len(path) > 64:
            raise ConfigError("Client configuration is too deeply nested")
        if start >= len(self.text):
            raise ConfigError("Incomplete JSON configuration")
        char = self.text[start]
        if char in "{[":
            is_object = char == "{"
            value = {} if is_object else []
            closing = "}" if is_object else "]"
            self.position += 1
            self.members[path] = {}
            while (
                self._space() < len(self.text) and self.text[self.position] != closing
            ):
                key_start = self.position
                if is_object:
                    key, length = json.JSONDecoder().raw_decode(
                        self.text[self.position :]
                    )
                    if not isinstance(key, str) or key in value:
                        raise ConfigError("Duplicate or non-string JSON key")
                    self.position += length
                    if self.text[self._space() : self.position + 1] != ":":
                        raise ConfigError("Expected a JSON colon")
                    self.position += 1
                else:
                    key = len(value)
                item = self._value((*path, key))
                if is_object:
                    value[key] = item
                else:
                    value.append(item)
                self.members[path][key] = key_start
                self._space()
                if self.text[self.position : self.position + 1] == ",":
                    self.position += 1
                elif self.text[self.position : self.position + 1] != closing:
                    raise ConfigError("Expected a JSON comma")
            if self.text[self.position : self.position + 1] != closing:
                raise ConfigError("Unclosed JSON configuration")
            self.position += 1
        else:
            value, length = json.JSONDecoder().raw_decode(self.text[start:])
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise ConfigError("Invalid JSON value")
            if isinstance(value, float) and not math.isfinite(value):
                raise ConfigError("Non-finite numbers are not valid JSON")
            self.position += length
        self.spans[path] = (start, self.position)
        return value

    def replace(self, path: tuple[str, ...], value):
        if path in self.spans:
            start, end = self.spans[path]
            if value is not None:
                return (
                    self.text[:start]
                    + json.dumps(value, ensure_ascii=False, indent=2)
                    + self.text[end:]
                )
            parent = path[:-1]
            key_start = self.members[parent][path[-1]]
            self.position = end
            comma = self._space()
            if self.text[comma : comma + 1] == ",":
                return (
                    self.text[:key_start]
                    + self.text[end:comma]
                    + self.text[comma + 1 :]
                )
            siblings = list(self.members[parent])
            index = siblings.index(path[-1])
            if index:
                previous_end = self.spans[(*parent, siblings[index - 1])][1]
                self.position = previous_end
                comma = self._space()
                return (
                    self.text[:comma]
                    + self.text[comma + 1 : key_start]
                    + self.text[end:]
                )
            return self.text[:key_start] + self.text[end:]
        if value is None:
            return self.text
        parent = path[:-1]
        if parent not in self.spans:
            return self.replace(parent, {path[-1]: value})
        target = lookup(self.value, parent)
        if not isinstance(target, dict):
            raise ConfigError("MCP parent is not an object; use manual configuration")
        _start, end = self.spans[parent]
        insert = end - 1
        if target:
            last = list(target)[-1]
            self.position = self.spans[(*parent, last)][1]
            if self.text[self._space() : self.position + 1] != ",":
                # Insert a comma immediately after the last value, before comments.
                last_end = self.spans[(*parent, last)][1]
                updated = self.text[:last_end] + "," + self.text[last_end:]
                return JsonDocument(updated).replace(path, value)
        addition = (
            "\n"
            + json.dumps(path[-1])
            + ": "
            + json.dumps(value, ensure_ascii=False, indent=2)
            + "\n"
        )
        return self.text[:insert] + addition + self.text[insert:]


def lookup(document, path):
    for key in path:
        if not isinstance(document, Mapping):
            raise ConfigError("Unsupported client configuration layout")
        if key not in document:
            return None
        document = document[key]
    return document


def parse(text: str, format: str):
    if format == "toml":
        import tomlkit

        return tomlkit.parse(text)
    if format == "yaml":
        from ruamel.yaml import YAML
        from ruamel.yaml.events import AliasEvent

        yaml = YAML(typ="rt")
        yaml.preserve_quotes = True
        if any(isinstance(event, AliasEvent) for event in yaml.parse(text)):
            raise ConfigError(
                "YAML aliases require manual configuration to avoid changing shared settings; use generic export"
            )
        document = yaml.load(text) or {}
        if not isinstance(document, Mapping):
            raise ConfigError("YAML configuration must be a mapping")
        return document
    return JsonDocument(text or "{}").value


def edit(text: str, format: str, path: tuple[str, ...], value) -> str:
    if format == "json":
        current = lookup(parse(text, format), path)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            for key in dict.fromkeys([*current, *value]):
                if current.get(key) != value.get(key) or (key in current) != (
                    key in value
                ):
                    text = edit(text, format, (*path, key), value.get(key))
            return text
        result = JsonDocument(text or "{}").replace(path, value)
        JsonDocument(result)
        return result
    document = parse(text, format)
    target = document
    for key in path[:-1]:
        if key not in target:
            target[key] = {}
        target = target[key]
        if not isinstance(target, Mapping):
            raise ConfigError("Unsupported configuration layout")
    if value is None:
        target.pop(path[-1], None)
    else:
        # Preserve comments attached to existing keys in round-trip documents.
        current = target.get(path[-1])
        if isinstance(current, Mapping):
            for key in list(current):
                if key not in value:
                    del current[key]
            current.update(value)
        else:
            target[path[-1]] = value
    if format == "toml":
        import tomlkit

        return tomlkit.dumps(document)
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    output = io.StringIO()
    yaml.dump(document, output)
    return output.getvalue()
