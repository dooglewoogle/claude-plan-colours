# Claude Plan Colours — Setup

You are installing the **Coloured Plan Viewer** for Claude Code. This system renders plan-mode markdown files as styled, colour-coded HTML in the user's browser. Follow every step below exactly.

## What this installs

- A **PostToolUse hook** that fires when Claude writes any file under `~/.claude/plans/`
- A **Python renderer** that converts plan markdown (with `[text:colour]` tags) to styled HTML
- A **hook entry in `~/.claude/settings.json`** so the system activates automatically

## Prerequisites — check these first

Run each of these and report any failures to the user before continuing:

```bash
python3 --version        # Must be 3.8+
python3 -c "import markdown; print('ok')"  # If this fails, run: pip3 install markdown
```

If `markdown` is not installed, install it:

```bash
pip3 install markdown
```

**Windows note:** If `python3` is not found, try `python` — depending on how Python was installed on Windows, only `python` may be on PATH. Use whichever works for all commands below and in the hook config.

## Step 1 — Create the hooks directory

```bash
mkdir -p ~/.claude/hooks
```

## Step 2 — Copy the renderer

Copy the source file from this directory into `~/.claude/hooks/`:

- `plan-render.py` → `~/.claude/hooks/plan-render.py`

Use the Read tool to read the file from this directory, then use the Write tool to write it to the destination path. Do NOT paraphrase or modify the file contents — copy it exactly.

## Step 3 — Register the hook in settings.json

Read `~/.claude/settings.json`. Merge the following hook configuration into the existing JSON, preserving all existing keys:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/plan-render.py"
          }
        ]
      }
    ]
  }
}
```

**Windows note:** If the user's system uses `python` instead of `python3`, substitute accordingly in the command above.

**Important merge rules:**

- If `hooks` key already exists, check if a `PostToolUse` array entry with `matcher: "Write"` already exists
- If it does and already points at `plan-render.py`, leave it alone
- If `hooks.PostToolUse` exists with other matchers, append this entry to the array
- Never remove or overwrite existing hook entries

## Step 4 — Verify

Run this smoke test:

```bash
# Create a test plan file and hook input
mkdir -p ~/.claude/plans

cat > /tmp/claude-plan-colours-test.md << 'TESTEOF'
# Test Plan
- [Green item:green]
- [Red warning:red]
- Normal item
TESTEOF

# Render it via stdin JSON (same as the hook would)
echo '{"tool_input":{"file_path":"/tmp/claude-plan-colours-test.md"}}' | python3 ~/.claude/hooks/plan-render.py

# Whoops — that will exit 0 because the path doesn't contain /.claude/plans/
# So test with a real plan path instead:
cp /tmp/claude-plan-colours-test.md ~/.claude/plans/test-plan.md
echo '{"tool_input":{"file_path":"'"$HOME"'/.claude/plans/test-plan.md"}}' | python3 ~/.claude/hooks/plan-render.py

# Check output exists and has colour tags
test -f ~/.claude/plans/test-plan.html && grep -c 'style="color:' ~/.claude/plans/test-plan.html

# Clean up
rm -f /tmp/claude-plan-colours-test.md ~/.claude/plans/test-plan.md ~/.claude/plans/test-plan.html ~/.claude/plans/.viewer-open-test-plan
```

Expected output: `2` (two colour spans). If you get this, tell the user setup is complete.

## Step 5 — Determine color preferences

now we need to figure out how to develop a colour palette that is pleasing to the user, and not actively harmful. a particular background color can either make it much easier or much harder to read text.
With this information we're going to build a palette and persist that. the palette needs to both respect the user preference but also provide a stable mapping of entity type that can be reused constantly. entities include: - classes - functions - variables - strings - files - components - libraries/packages - systems - concepts - titles/sections - etc

Invoke the AskUserQuestion tool to figure out what kinds of colours and color combinations work for the user.
Examples:

- Do you find it easier reading with a background that's blue, yellow, neutral or something else?
- Would you like me to use highly contrasting colours or be more subtle?
- Are there any colours that hurt to look at?

Think about those answers, Then ask more questions if required, then based on what the user has indicated write the palette into the preferences section of 'goes-in-claude-md.md'.

Finally, append the entirety of 'goes-in-claude-md.md' to '~/.claude/CLAUDE.md'

## Step 6 — Report to user

Tell the user:

> Plan viewer installed. When you enter plan mode, the hook will render your plan as coloured HTML and open it in your browser. Use `[text:colour]` syntax in plan files for colour coding. To reset the browser auto-open (e.g. after closing the tab), run: `rm ~/.claude/plans/.viewer-open`

## Platform support

| Platform | First open     | Subsequent updates                                | Notes                                                       |
| -------- | -------------- | ------------------------------------------------- | ----------------------------------------------------------- |
| macOS    | `open` command | AppleScript browser reload, falls back to re-open | No polling needed                                           |
| Linux    | `xdg-open`     | `<meta refresh>` polling (2s)                     | Re-opens browser on every write                             |
| Windows  | `os.startfile` | `<meta refresh>` polling (2s)                     | May need `python` instead of `python3` in hook command      |
