# Claude Plan Colours

Claude Code tends to output a LOT of text, and often it's very visually similar.
For anyone who struggles to read large chunks of text this is a problem.

It's difficult to read the big plans.

It's difficult to read the questions and descriptions.

**Claude Plans Colours does two things**

1. Adds PostToolUse hook that intercepts plan file writes and renders them as styled, colour-coded HTML in your browser.
2. Adds some targeted instructions to the users CLAUDE.md to make all output less "Big Blobs of Text"

## How it works

- Claude is instructed to use a specific tag format for color when writing plans.
- Plans land in `~/.claude/plans/` as `.md` files
- Each gets a matching `.html` file
- The browser is opened, or refreshed to view the plan.

## Example

```markdown
The [Pet:#0D7377] class calls [applyDecay:#2656A8] to update [hunger:#B35000]
```

Renders as coloured spans in the browser — classes in teal, functions in blue, variables in orange, etc.

## Platform support

|             | First open     | Updates                    | Status     |
| ----------- | -------------- | -------------------------- | ---------- |
| **macOS**   | `open`         | AppleScript browser reload | Tested     |
| **Linux**   | `xdg-open`     | Re-opens on each write     | Tested     |
| **Windows** | `os.startfile` | Re-opens on each write     | NOT Tested |

## Setup

`git clone`

`cd claude-plan-colours`

`claude "Follow the instructions in SETUP.md exactly"` (run from the cloned directory)

Restart Claude Code once done.

## Files

| File                   | Purpose                                                                  |
| ---------------------- | ------------------------------------------------------------------------ |
| `plan-render.py`       | Hook script — renders markdown to HTML, opens browser                    |
| `goes-in-claude-md.md` | Prompt instructions + colour palette (appended to `~/.claude/CLAUDE.md`) |
| `SETUP.md`             | Step-by-step installation guide                                          |
