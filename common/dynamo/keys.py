"""Key template rendering helpers.

Templates use Python str.format() style placeholders: "USER_ID@{user_id}".
"""
import re


_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")
_SPLIT_RE = re.compile(r"(\{\w+\})")


def placeholders(template: str) -> list[str]:
    """Extract placeholder names from a template, in order."""
    return _PLACEHOLDER_RE.findall(template)


def render_full(template: str, fields: dict) -> str:
    """
    Render a template requiring ALL placeholders present in `fields`
    (and non-empty). Raises ValueError if any are missing.
    """
    missing = [p for p in placeholders(template) if not fields.get(p)]
    if missing:
        raise ValueError(
            f"missing required fields {missing} for template {template!r}"
        )
    return template.format(**fields)


def render_partial(template: str, fields: dict) -> tuple[str, bool]:
    """
    Render a template up to the first missing placeholder.

    Returns (rendered_string, is_complete).
      - is_complete=True  → all placeholders were filled
      - is_complete=False → stopped at first missing placeholder
    If template has no placeholders, returns (template, True).
    """
    if not template:
        return "", True

    out: list[str] = []
    is_complete = True
    for tok in _SPLIT_RE.split(template):
        if tok.startswith("{") and tok.endswith("}"):
            name = tok[1:-1]
            val = fields.get(name)
            if val is None or val == "":
                is_complete = False
                break
            out.append(str(val))
        else:
            out.append(tok)
    return "".join(out), is_complete
