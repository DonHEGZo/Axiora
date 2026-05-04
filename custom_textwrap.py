"""Custom text wrapping and filling utilities.
This is a minimal implementation to avoid circular imports.
"""

def dedent(text):
    """Remove any common leading whitespace from every line in `text`."""
    import re
    # Look for the longest leading string of spaces and tabs common to
    # all lines.
    margin = None
    text = str(text).expandtabs()
    indents = re.compile(r'^\s*').findall(text)
    for indent in indents:
        if margin is None:
            margin = indent
        else:
            # Current line more deeply indented than previous winner:
            # no change (previous winner is still on top).
            if indent.startswith(margin):
                continue
            # Current line consistent with and no deeper than previous winner:
            # it's the new winner.
            if margin.startswith(indent):
                margin = indent
            # Find the common whitespace between current line and previous winner.
            else:
                for i, (x, y) in enumerate(zip(margin, indent)):
                    if x != y:
                        margin = margin[:i]
                        break
    if margin:
        text = re.sub(r'(?m)^' + margin, '', text)
    return text 