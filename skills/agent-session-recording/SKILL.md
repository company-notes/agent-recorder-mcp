---
name: agent-session-recording
description: >-
  Install and configure the agent-recorder MCP from this skill, then record the
  agent's own browser/computer-use session and return a replay link. Use when
  the user shares this skill to set up recording, requests installation, asks
  for a replay, or wants browser/computer UI work recorded. If the recording
  tools are missing, set up the MCP connector before recording.
---
# Agent session recording

**This skill is the installation entry point.** When a user gives you this
SKILL.md URL, installs this skill, or asks to set up agent recording, start
with the bootstrap steps below. Do **not** require the user to install the MCP
server first or separately install this skill again.

The same SKILL.md works for different agent vendors. Recording requires an
agent that can use an MCP connector and access **its own** Linux X11 display;
it cannot capture a remote user's desktop. Windows, macOS and Wayland
recording are not implemented.

## Bootstrap: Skill first, then MCP

1. **Load/install this skill first.** If the user provided only a link and
   your client can install skills, install it through that client and
   continue these instructions. If the client can only read instructions,
   use them for this session and say if persistent skill installation is
   unavailable. Do not pretend reading a URL installs a skill.
2. **Check for the MCP tools.** Discover whether `startRecording`,
   `recordingStatus` and `finishRecording` are available. If they are,
   skip connector installation; do not replace a working connector.
3. **Identify the current agent and its connector setup method.** When the
   tools are missing, register the pinned `agent-recorder` MCP server using
   the appropriate method below. Perform supported tool/CLI/configuration
   actions yourself if permitted. Request approval when the client requires
   it. Do not ask the user to manually follow a command you can run.
4. **Reload/reconnect if necessary.** Refresh MCP discovery (or restart the
   client when required) and check that `startRecording`,
   `recordingStatus`, and `finishRecording` are now available. Reading
   a config file alone is not proof the MCP server is running.
5. **Report the result.** Say whether the skill was installed/persisted,
   whether the MCP connector was registered, and whether its tools were
   verified. If you lack permission or cannot register a connector, provide
   the exact outstanding approval or action; never claim success prematurely.

This is a one-way bootstrap: **Skill → MCP**. The MCP installer may also
copy skill files for some local clients as a convenience, but installing the
MCP is not a prerequisite for installing or reading this skill.

### Pinned MCP source

Install only `v0.2.2`, not an unpinned default branch:

```text
git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.2
```

Common stdio MCP connector entry:

```json
{
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.2",
    "agent-recorder-mcp"
  ]
}
```

### Agent-specific connector installation

- **Grok Bot:** Use its **custom connector** setup with command `uvx`
  and arguments `--from git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.2 agent-recorder-mcp`.
  Grok Bot is **not** Grok Build. If its custom connector can only be
  managed through a user approval/UI unavailable to you, ask the user to
  approve or add the entry, then recheck the tools. Do not run the Grok
  Build installer for Grok Bot.
- **Grok Build:** If shell access is available, run:
  `uvx --from git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.2 agent-recorder-mcp install --target grok-build`.
  This writes the Grok Build MCP configuration, not the Grok Bot connector.
- **Claude Code:** With shell access run:
  `uvx --from git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.2 agent-recorder-mcp install --target claude-code`.
  Alternatively use `claude mcp add-json agent-recorder --scope user`
  with the stdio entry above.
- **Claude Desktop:** Register the stdio entry under `mcpServers` in
  `claude_desktop_config.json`. Desktop skill availability is separate
  from its MCP configuration; follow the client's skill installation rules.
- **Codex:** With shell access run:
  `uvx --from git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.2 agent-recorder-mcp install --target codex`.
  Alternatively configure `[mcp_servers.agent-recorder]` in
  `~/.codex/config.toml` using `command = "uvx"` and corresponding `args`.
- **Cursor:** Add the stdio entry under `mcpServers` in
  `~/.cursor/mcp.json`, using supported client configuration tools.
- **Other agents:** If the client supports a stdio MCP connection, register
  the common entry above using its own MCP configuration mechanism. If it
  does not, report the limitation instead of claiming universal support.

The runtime needs Python 3.11+ via `uvx`, `ffmpeg`, and `xdpyinfo` or
`xwininfo` (usually `x11-utils`) on Linux X11. If these are missing,
install them only when the environment and permissions allow; otherwise
report what is required. Connector installation and file sharing may
require user approval. Respect every prompt.

### When the skill was supplied as a URL

A user can share the canonical, versioned SKILL.md directly:

```text
https://raw.githubusercontent.com/company-notes/agent-recorder-mcp/v0.2.2/skills/agent-session-recording/SKILL.md
```

Start at **Bootstrap: Skill first, then MCP**. The user should not need
to discover the Repository, choose an MCP installer, or know MCP configuration
details. Reuse these instructions when the skill is subsequently invoked.
Do not run `agent-recorder-mcp install-skill` as a bootstrap prerequisite:
that command only helps copy an already available skill to other locations.

## Record browser/computer work

After the connector tools are verified:

1. Before the first browser/computer UI action, call `startRecording`.
   Set `fps` or `maxDurationSeconds` only if requested. Default FFL
   sharing needs no custom `outputDir`.
2. Perform the user's task on the agent's own browser/computer.
3. Call `finishRecording` after the last UI action.
4. Include the returned replay `url` in the final response, together with
   a recording summary: the time span and duration, then a short numbered
   list of what was done in the recording (key steps, accounts and systems
   touched, anything created or changed, human help such as 2FA, and any
   mistakes or detours and how they were fixed). Never put passwords,
   codes or key contents in the summary.
5. If recording fails, continue only if safe, and clearly state that no
   replay was produced and why.
6. Do not record tasks without browser/computer UI unless explicitly asked.

Do not read the video into the conversation. The model gets a replay link.
For managed-sandbox synthetic DNS, FFL chooses a web relay automatically;
otherwise it keeps its P2P-first behavior. The local recording is retained
until FFL reports a completed download.

## Google Drive

If the user requests Google Drive delivery and a Drive connector exists:

1. Start with `startRecording(outputDir=...)` pointing to an existing
   directory the upload connector can read.
2. Finish with `finishRecording(delivery="google_drive", cleanup="after_upload")`.
3. Upload the returned `localPath` with that connector, without reading
   the video into the conversation.
4. Call `confirmUpload(recordingId=..., url=...)` using the actual Drive URL.
5. Return the Drive URL.

Without a Drive connector, explain the limitation and use the normal
FastFileLink replay if appropriate.

## Final response

Reply in the user's language. For setup requests, distinguish skill
installation, MCP registration and actual tool availability. For recording
requests, include the work result, the replay URL and its recording summary, or state why no
replay exists. Never imply that installing a skill alone bypasses agent
permission controls or enables unsupported X11 capture.
