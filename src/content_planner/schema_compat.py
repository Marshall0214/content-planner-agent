"""Finite local-reference expansion for Ollama's outgoing tool schemas only."""
from copy import deepcopy
import re
from urllib.parse import unquote


class SchemaReferenceError(ValueError):
    pass


def inline_local_refs(schema):
    """Copy and inline document-local JSON Pointers; fail closed on bad/cyclic refs.

    Sibling constraints apply together with the referenced schema. Conflicting
    keys use allOf rather than silently replacing either constraint. Definition
    registries at the root are removed only after their contents were checked.
    """
    root = deepcopy(schema)

    def resolve(ref):
        if not isinstance(ref, str) or not (ref == "#" or ref.startswith("#/")):
            raise SchemaReferenceError(f"Only local JSON Pointer references are supported: {ref!r}")
        if re.search(r"%(?![0-9a-fA-F]{2})", ref):
            raise SchemaReferenceError(f"Invalid reference escape: {ref!r}")
        pointer = unquote(ref[1:], errors="strict")
        tokens = [] if not pointer else pointer[1:].split("/")
        if any(re.search(r"~(?![01])", token) for token in tokens):
            raise SchemaReferenceError(f"Invalid JSON Pointer escape: {ref!r}")
        tokens = tuple(t.replace("~1", "/").replace("~0", "~") for t in tokens)
        target = root
        try:
            for token in tokens:
                if isinstance(target, dict):
                    target = target[token]
                elif isinstance(target, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
                    target = target[int(token)]
                else:
                    raise KeyError(token)
        except (KeyError, IndexError) as exc:
            raise SchemaReferenceError(f"Missing local schema reference: {ref!r}") from exc
        if not isinstance(target, (dict, bool)):
            raise SchemaReferenceError(f"Reference must target a schema object or boolean: {ref!r}")
        return target, tokens

    def expand(node, active):
        if isinstance(node, list):
            return [expand(item, active) for item in node]
        if not isinstance(node, dict):
            return deepcopy(node)
        if "$ref" in node:
            target, identity = resolve(node["$ref"])
            if identity in active:
                raise SchemaReferenceError(f"Cyclic local schema reference: {node['$ref']!r}")
            expanded = expand(target, (*active, identity))
            siblings = expand({k: v for k, v in node.items() if k != "$ref"}, active)
            if not siblings:
                return expanded
            if isinstance(expanded, dict) and all(k not in expanded or expanded[k] == v for k, v in siblings.items()):
                return {**expanded, **siblings}
            return {"allOf": [expanded, siblings]}
        # These keywords contain instance data, not nested schema references.
        return {key: deepcopy(value) if key in ("enum", "const", "default", "examples") else expand(value, active)
                for key, value in node.items()}

    result = expand(root, ())
    if isinstance(result, dict):
        result.pop("$defs", None)
        result.pop("definitions", None)
    return result


def ollama_tool_definitions(definitions):
    """Never mutate shared/Pydantic/cloud definitions."""
    copied = deepcopy(definitions)
    for tool in copied:
        tool["parameters"] = inline_local_refs(tool["parameters"])
    return copied
