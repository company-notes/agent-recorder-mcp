---
name: agent-session-recording
description: >
  Record an agent's own Linux X11 desktop while it uses a browser or computer
  UI, and return a session replay link. Use for browser/computer-use work or
  when the user explicitly requests a replay. Start before the first UI action,
  finish before the final answer. Install the agent-recorder MCP connector when
  its tools are missing.
---

# Agent session recording

This skill is independent of the agent vendor. It requires an agent environment
that can load `SKILL.md`, run an MCP connector, and access its **own** Linux X11
display. It never records a remote user's personal desktop. Platforms without
X11 capture or a supported MCP connection cannot record, even if they load the
skill.

Source revision: `v0.2.0`

```text
git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.0
```

Use this revision for installation, not an unpinned default branch.

## Connector setup

Check for `startRecording` first. If it is unavailable, configure the MCP
server for the current agent using its supported connector configuration.
Do not assume that placing a skill file automatically registers the MCP server.

Common stdio connector entry:

```json
{
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.0",
    "agent-recorder-mcp"
  ]
}
```

- **Grok Bot**: add the entry as a custom connector. This is distinct from
  Grok Build's `~/.grok/config.toml`.
- **Grok Build**: use `agent-recorder-mcp install --target grok-build`.
- **Claude Code**: use `agent-recorder-mcp install --target claude-code`,
  or `claude mcp add-json agent-recorder --scope user` with the JSON entry.
- **Claude Desktop**: register the entry in `claude_desktop_config.json` under
  `mcpServers`. Desktop skill loading is separate from MCP configuration.
- **Codex**: use `agent-recorder-mcp install --target codex`, or place
  `[mcp_servers.agent-recorder]` in `~/.codex/config.toml` with
  `command = "uvx"` and the corresponding `args`.
- **Cursor**: register the JSON entry under `mcpServers` in
  `~/.cursor/mcp.json`.
- **Other agents**: use their supported stdio MCP configuration with the
  command and arguments above. If they do not load skills automatically,
  attach these instructions through their supported mechanism.

To install this skill for local agents from a checkout or installed package:

```sh
agent-recorder-mcp install-skill --target grok,claude,codex,cursor,copilot --overwrite
```

For other `SKILL.md`-compatible agents, use
`agent-recorder-mcp install-skill --directory /path/to/agent/skills`.
The skill install is separate from registering its MCP connector.

The agent computer requires Python 3.11+ via `uvx`, `ffmpeg`, and
`xdpyinfo` or `xwininfo` for Linux X11. Adding a connector, creating an FFL
share, and uploading a file can require explicit user approval. Respect those
prompts and never bypass them.

## Record browser/computer work

1. Before the first browser or computer UI action, call `startRecording`.
   Only customize `fps` or `maxDurationSeconds` when the user requests it.
   Use the default recording directory for FastFileLink. For Google Drive,
   supply `outputDir` as an existing directory readable by its upload tool.
2. Perform the user's browser/computer task with the available agent tools.
3. After the final UI action, call `finishRecording`.
4. Include its returned `url` in the final response as the session replay.
5. If recording fails, continue the main task only if safe, and explain that
   no replay was produced and why.
6. Do not record a task with no browser/computer UI unless explicitly requested.

Never load the video bytes into the model conversation. The MCP returns a link,
not the recording itself.

The default `finishRecording` shares via FastFileLink. It automatically chooses
web relay when the agent's DNS indicates a managed sandbox; otherwise it keeps
FFL's P2P-first behavior. The file stays local until a completed download
triggers cleanup.

## Google Drive

Only use this path if the user wants the replay on Google Drive and the agent
has an upload connector:

1. Call `startRecording(outputDir=...)` with a directory the upload connector
   can read, for example `/workspace` when available.
2. Call `finishRecording(delivery="google_drive", cleanup="after_upload")`.
3. Upload the returned `localPath` with the connected Drive tool without
   reading the file into the chat.
4. Call `confirmUpload(recordingId=..., url=...)` with the uploaded file link.
5. Include the Google Drive link in the final response.

If Google Drive is unavailable, default to an FFL share and explain the change.

## Final answer

Reply in the user's language. When the replay succeeds, give the task result
and the replay URL. Otherwise give the task result and the recording failure
reason. Do not claim a replay exists when there is no URL.
