"""
Diff Generator
Produces unified diffs between original and migrated PHP source.
"""
import difflib
import html


def generate_diff(original: str, migrated: str, file_path: str) -> str:
    """
    Generate a unified diff between *original* and *migrated*.

    Returns an empty string if the two strings are identical.

    Parameters
    ----------
    original : str
        The original PHP source.
    migrated : str
        The migrated PHP source.
    file_path : str
        Used as the filename header in the diff output.

    Returns
    -------
    str
        A unified diff string, or ``""`` if there are no changes.
    """
    if original == migrated:
        return ""

    original_lines = original.splitlines(keepends=True)
    migrated_lines = migrated.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        migrated_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    return "\n".join(diff)


def diff_to_html(diff: str) -> str:
    """
    Convert a unified diff string to a simple HTML representation.

    Each line is wrapped in a ``<span>`` with one of these CSS classes:
    - ``diff-add`` — added lines (``+``)
    - ``diff-del`` — removed lines (``-``)
    - ``diff-hunk`` — hunk headers (``@@``)
    - ``diff-meta`` — file header lines (``---`` / ``+++``)

    Parameters
    ----------
    diff : str
        Unified diff string produced by :func:`generate_diff`.

    Returns
    -------
    str
        HTML string.  Returns an empty string for an empty diff.
    """
    if not diff:
        return ""

    lines = diff.splitlines()
    html_parts = ['<pre class="evua-diff">']

    for line in lines:
        escaped = html.escape(line)
        if line.startswith("+++") or line.startswith("---"):
            html_parts.append(f'<span class="diff-meta">{escaped}</span>')
        elif line.startswith("+"):
            html_parts.append(f'<span class="diff-add">{escaped}</span>')
        elif line.startswith("-"):
            html_parts.append(f'<span class="diff-del">{escaped}</span>')
        elif line.startswith("@@"):
            html_parts.append(f'<span class="diff-hunk">{escaped}</span>')
        else:
            html_parts.append(f'<span class="diff-ctx">{escaped}</span>')

    html_parts.append("</pre>")
    return "\n".join(html_parts)
