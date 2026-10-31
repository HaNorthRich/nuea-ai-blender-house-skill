# Install guide for Claude

The user sent you this repository and asked you to install the skill. Work through the steps in order. Each step
ends on a check: run it, read its output, and tell the user the result in their language.

- Before each step, tell the user in one line what you will run and why.
- Ask the user first before you install software (git, uv, Blender) or replace a copy of the skill already installed.
- A check that fails, or a "no" from the user: stop there, show the user the step and its output, and ask how they
  want to go on. A step starts only after the step before it passed its check.
- Your shell forgets variables between commands: write the real paths into every command, in double quotes (Blender
  paths often contain spaces), and run each code block below as one command.
- Steps marked **user** need the user's hands: say exactly what to click, then wait for their answer.

## 0. A shell and git

This skill needs Claude Code (the terminal app, the Code tab of the Claude desktop app, or an IDE extension),
because it installs files and runs Blender. Claude Code comes with the paid Claude plans (Pro and up) or an API key.

- No shell available (a chat-only Claude): tell the user to open Claude Code and paste
  `ลง Skill นี้ให้หน่อย https://github.com/HaNorthRich/nuea-ai-blender-house-skill`, then stop.
- Run `git --version`. Without git, step 3 downloads a tarball with `curl` instead (no install needed).
- **Check:** a shell runs commands, and you know whether git is there.

## 1. Blender 4.2 or newer

Find the Blender executable and run it with `--version`:

| OS | Usual path |
|---|---|
| macOS | `/Applications/Blender.app/Contents/MacOS/Blender` |
| Windows (Git Bash) | `/c/Program Files/Blender Foundation/Blender <version>/blender.exe`, or `where blender` |
| Linux | `command -v blender`; snap `/snap/bin/blender`; flatpak `flatpak run org.blender.Blender` |

This guide calls that path BLENDER. If Blender is missing or older than 4.2, ask the user to install the current
release from https://www.blender.org/download/ and wait for them to say it is done.

- **Check:** `"<BLENDER>" --version` prints `Blender 4.2` or newer. Note the major.minor version (e.g. `5.2`).

## 2. uv

Run `uvx --version`. If it is missing, ask, then install uv with its official installer and show the user the URL
first: macOS `brew install uv` (or `curl -LsSf https://astral.sh/uv/install.sh | sh`), Linux the same curl line,
Windows `winget install --id=astral-sh.uv -e`. The curl installer adds uv to the PATH in the shell profile; open a
new shell if `uvx` is still not found.

- **Check:** `uvx --version` prints a version.

## 3. The skill

If `~/.claude/skills/nuea-ai-blender-house` already exists, this is an update. Ask; on yes, move the old copy out of
the skills folder (two folders with the same skill name would both load):

```bash
mv ~/.claude/skills/nuea-ai-blender-house ~/.claude/nuea-ai-blender-house.bak-$(date +%Y%m%d%H%M%S)
```

On no, keep the installed copy as it is and go to step 4.

Then fetch and copy, as one command (with git):

```bash
SRC="$(mktemp -d)" && git clone --depth 1 https://github.com/HaNorthRich/nuea-ai-blender-house-skill.git "$SRC/repo" && mkdir -p ~/.claude/skills && cp -R "$SRC/repo/nuea-ai-blender-house" ~/.claude/skills/
```

Without git:

```bash
SRC="$(mktemp -d)" && curl -fsSL https://github.com/HaNorthRich/nuea-ai-blender-house-skill/archive/refs/heads/main.tar.gz | tar -xz -C "$SRC" && mkdir -p ~/.claude/skills && cp -R "$SRC/nuea-ai-blender-house-skill-main/nuea-ai-blender-house" ~/.claude/skills/
```

- **Check:** `head -3 ~/.claude/skills/nuea-ai-blender-house/SKILL.md` shows `name: nuea-ai-blender-house`.

## 4. Blender MCP (Claude Code ↔ Blender)

Tell the user in one line: this MCP lets Claude run Python inside their Blender; that is how the skill models.

Run `claude mcp list`.

- `claude` not found (some desktop-app setups have no CLI): stop, and give the user the two commands below to run
  in a terminal once Claude Code's CLI is installed (https://claude.com/claude-code).
- A server whose command runs `mcp-for-blender`, or `blender-mcp` (its old PyPI name), is the one this skill uses:
  keep it as it is and go to step 5.
- A server named `blender` that runs anything else may be a different Blender MCP: ask the user whether to replace
  it (`claude mcp remove blender --scope user`, then the commands below).

Otherwise register it with uvx's full path, so a Claude app started from the desktop finds it too:

```bash
uvx mcp-for-blender install-addon && claude mcp add --scope user blender "$(command -v uvx)" mcp-for-blender
```

On Windows, register the path that `where uvx` prints (a `C:\…\uvx.exe` path) instead of `$(command -v uvx)`.

- **Check:** `install-addon` printed the add-on file it wrote (`blender_mcp.py`) under the Blender version from
  step 1, and `claude mcp list` lists `blender` running `mcp-for-blender`.

## 5. Proof that it works (offer it: about 2 minutes, no user input)

Build the worked example house from an empty Blender, with every stage's selfcheck. `E42_OUT` saves the result in
the user's home folder, where they can open it (Windows Git Bash: `E42_OUT="$(cygpath -m "$HOME")/e42_house.blend"`):

```bash
E42_OUT="$HOME/e42_house.blend" "<BLENDER>" -b --factory-startup --python-exit-code 1 -P ~/.claude/skills/nuea-ai-blender-house/examples/e42/scripts/build_all.py
```

- **Check:** exit code 0, 10 stage lines from `ST00–ST05` to `ST14` each with `ok` and its quantities, then
  `BUILD DONE <path>`.

## 6. Hand over (**user**)

Tell the user what is installed (the skill folder, the Blender add-on, the `blender` MCP server) and give them
these steps:

1. Open Blender → **Edit → Preferences → Add-ons**, search "MCP for Blender" and enable **Interface: MCP for
   Blender**. In the 3D viewport press **N**, open the **MCP for Blender** tab, and click **Start MCP Server** if it
   is not running.
2. Quit Claude Code completely and open it again: skills and MCP servers load when a session starts.
3. In the new session, type `เช็กสถานะ Blender`. When the link works, Claude calls the Blender MCP tool
   `get_addon_status` and answers with the Blender version.
4. If step 5 ran: open `~/e42_house.blend` in Blender to see the example house, built stage by stage.
5. Then try, for example: `ปั้น 3D บ้านจากแปลนนี้ใน Blender หลังคาปั้นหยา แล้ว render ภาพขาย 4 มุม` (with a plan
   attached), or `ปั้นตามลำดับก่อสร้าง เริ่มจากฐานราก ผมจะส่งสเปกให้ทีละขั้น`.

**Done when** the user has the steps above and every check in steps 0–4 passed (step 5 too, if they took it).
