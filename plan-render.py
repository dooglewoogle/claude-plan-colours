#!/usr/bin/env python3
"""Render Claude Code plan markdown to styled HTML and display in browser.

Called directly as a PostToolUse hook (no shell wrapper).
Reads hook JSON from stdin to extract the written file path.

Platform behaviour:
  macOS   — AppleScript-based browser reload (instant, no polling).
            Falls back to re-opening browser if reload fails.
  Linux   — <meta http-equiv="refresh"> polling (2s) + xdg-open on first view.
  Windows — <meta http-equiv="refresh"> polling (2s) + os.startfile on first view.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLANS_DIR = Path.home() / ".claude" / "plans"

# ---------------------------------------------------------------------------
# Tag substitution
# ---------------------------------------------------------------------------

def apply_tags(text: str) -> str:
    """Replace [text:colour] with coloured <span>s.

    Colour can be a CSS name (red, dodgerblue) or hex (#fa8072).
    """
    def _replace(m: re.Match) -> str:
        content, colour = m.group(1), m.group(2)
        return f'<span style="color:{colour}">{content}</span>'
    return re.sub(r'\[([^\]]+?):([a-zA-Z#][a-zA-Z0-9#]*)\]', _replace, text)

# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def render_html(source: str, *, use_meta_refresh: bool) -> str:
    try:
        import markdown
        body = markdown.markdown(
            apply_tags(source),
            extensions=["tables", "fenced_code"],
        )
    except ImportError:
        # No markdown package — raw pre-formatted fallback
        from html import escape
        body = f"<pre>{apply_tags(escape(source))}</pre>"

    refresh = '<meta http-equiv="refresh" content="2">' if use_meta_refresh else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  {refresh}
  <style>
    @import url('https://fonts.cdnfonts.com/css/opendyslexic');
    body {{
      font-family: 'OpenDyslexic', Arial, sans-serif;
      font-size: 16px;
      line-height: 1.8;
      max-width: 1400px;
      margin: 40px auto;
      padding: 0 24px;
      background: #FDF6E3;
      color: #3B3228;
    }}
    h1, h2, h3 {{ color: #6B3FA0; margin-top: 1.6em; }}
    h1 {{ border-bottom: 2px solid #D4C5A9; padding-bottom: 0.3em; }}
    h2 {{ border-bottom: 1px solid #D4C5A9; padding-bottom: 0.2em; }}
    code {{
      background: #EDE8D5;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 0.9em;
    }}
    pre {{
      background: #EDE8D5;
      padding: 16px;
      border-radius: 6px;
      overflow-x: auto;
      line-height: 1.4;
    }}
    pre code {{ background: none; padding: 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
    th, td {{ border: 1px solid #D4C5A9; padding: 8px 12px; text-align: left; }}
    th {{ background: #EDE8D5; color: #6B3FA0; }}
    a {{ color: #2656A8; }}
    blockquote {{
      border-left: 4px solid #6B3FA0;
      margin: 1em 0;
      padding: 0.5em 1em;
      background: #EDE8D5;
    }}
    ul, ol {{ padding-left: 1.5em; }}
    li {{ margin: 0.3em 0; }}
    li > ul, li > ol {{ margin-top: 0.2em; }}
    hr {{ border: none; border-top: 1px solid #D4C5A9; margin: 2em 0; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

_SYSTEM = platform.system()

def is_mac() -> bool:
    return _SYSTEM == "Darwin"

def is_windows() -> bool:
    return _SYSTEM == "Windows"

# ---------------------------------------------------------------------------
# macOS — AppleScript browser reload
# ---------------------------------------------------------------------------

_RELOAD_SCRIPTS = {
    "Safari": (
        'tell application "Safari"\n'
        '  if (count of windows) > 0 then\n'
        '    tell front document to do JavaScript "location.reload()"\n'
        '  end if\n'
        'end tell'
    ),
    "Google Chrome": (
        'tell application "Google Chrome"\n'
        '  if (count of windows) > 0 then\n'
        '    tell active tab of front window to reload\n'
        '  end if\n'
        'end tell'
    ),
    "Arc": (
        'tell application "Arc"\n'
        '  if (count of windows) > 0 then\n'
        '    tell front window to reload active tab\n'
        '  end if\n'
        'end tell'
    ),
}


def _browser_is_running(name: str) -> bool:
    """Check if a macOS app is currently running."""
    try:
        out = subprocess.run(
            ["osascript", "-e",
             f'tell application "System Events" to (name of processes) contains "{name}"'],
            capture_output=True, text=True, timeout=3,
        )
        return "true" in out.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def reload_browser_mac() -> bool:
    """Attempt AppleScript reload on the first running browser found."""
    for app, script in _RELOAD_SCRIPTS.items():
        if not _browser_is_running(app):
            continue
        try:
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=3,
            )
            if r.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return False

# ---------------------------------------------------------------------------
# Cross-platform browser open
# ---------------------------------------------------------------------------

def open_in_browser(path: Path) -> None:
    url = path.as_uri()
    if is_mac():
        subprocess.Popen(["open", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif is_windows():
        os.startfile(str(path))
    else:
        opener = shutil.which("xdg-open") or shutil.which("sensible-browser")
        if opener:
            subprocess.Popen([opener, url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Read hook JSON from stdin (PostToolUse payload)
    hook_input = json.loads(sys.stdin.read())
    tool_input = hook_input.get("tool_input", {})
    path_written = tool_input.get("file_path") or tool_input.get("path") or ""

    if not path_written:
        sys.exit(0)

    # Only act on plan files
    if "/.claude/plans/" not in path_written or not path_written.endswith(".md"):
        sys.exit(0)

    plan_path = Path(path_written).expanduser()
    if not plan_path.exists():
        print(f"Plan file not found: {plan_path}", file=sys.stderr)
        sys.exit(1)

    source = plan_path.read_text()

    # Derive HTML and marker paths from the plan filename
    plan_html = PLANS_DIR / f"{plan_path.stem}.html"
    open_marker = PLANS_DIR / f".viewer-open-{plan_path.stem}"

    # Mac gets instant reload via AppleScript — no need for meta-refresh.
    # Linux/Windows rely on meta-refresh polling as the reload mechanism.
    use_meta_refresh = not is_mac()

    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    plan_html.write_text(render_html(source, use_meta_refresh=use_meta_refresh))

    if is_mac():
        already_open = open_marker.exists()
        if already_open:
            # Try instant reload; if it fails (browser closed), re-open
            if not reload_browser_mac():
                open_in_browser(plan_html)
        else:
            open_in_browser(plan_html)
            open_marker.touch()
    else:
        # Linux/Windows: always re-open — no reliable way to detect closed tabs
        open_in_browser(plan_html)


if __name__ == "__main__":
    main()
