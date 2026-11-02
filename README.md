# agent-recorder-mcp

Local MCP server that records the computer an agent is using and returns a replay link when the task is done.

The recording stays on the agent machine. The model receives a link, not the video. FastFileLink is the delivery transport: the local file remains until the recipient finishes downloading.

Version **0.2.0** captures the **agent machine's** Linux X11 display, not the
user's desktop. This works with GrokBot and other agents when their runtime
exposes an X11 display, MCP tools, and a supported skill-loading mechanism.
Windows, macOS and Wayland capture are not implemented.

## Install

The canonical skill is [skills/agent-session-recording/SKILL.md](skills/agent-session-recording/SKILL.md).
It is **not GrokBot-specific**. One source is packaged with the MCP server and
installed into supported agent skill directories.

Use Python 3.11+ (via `uvx`), `ffmpeg`, and an X11 size tool (`xdpyinfo` or
`xwininfo`, usually from `x11-utils`). MCP registration, FFL sharing, and
Google Drive uploads may ask for user approval.

### Agent skill locations

| Agent | User skill location | MCP connector |
| --- | --- | --- |
| Grok Bot / Grok Build | `~/.grok/skills/agent-session-recording/SKILL.md` | Grok Bot custom connector / Grok Build installer |
| Claude Code | `~/.claude/skills/agent-session-recording/SKILL.md` | `install --target claude-code` |
| Codex | `~/.agents/skills/agent-session-recording/SKILL.md` | `install --target codex` |
| Cursor | `~/.cursor/skills/agent-session-recording/SKILL.md` | Configure `~/.cursor/mcp.json` |
| VS Code / Copilot | `~/.copilot/skills/agent-session-recording/SKILL.md` | Configure your MCP client |
| Other compatible agents | Custom `SKILL.md` directory | Configure your agent's stdio MCP client |

Install a matching MCP connector and skill for supported mcp-install clients:

```bash
uvx --from git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.0 \
  agent-recorder-mcp install --target claude-code,codex,grok-build --overwrite
```

The underlying `mcp-install` command accepts `claude-desktop`,
`claude-code`, `codex`, and `grok-build` (`all` is its default).
It installs skills only where a local skill directory is supported;
Claude Desktop's skill workflow is separate from MCP registration.

For GrokBot, Cursor, Copilot or other agents, install the portable skill
independently, then register the connector using the instructions in `SKILL.md`:

```bash
uvx --from git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.0 \
  agent-recorder-mcp install-skill --target grok,cursor,copilot --overwrite
```

For an agent with another skill directory:

```bash
agent-recorder-mcp install-skill --directory /path/to/agent/skills --overwrite
```

The destination is `/path/to/agent/skills/agent-session-recording/SKILL.md`.
You may also run `install-skill --target all` to copy the skill into all five
supported local directories. A skill installation does **not** automatically
register an MCP connector for clients lacking an installer backend.
The same MCP command for all compatible stdio clients is:

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

Some cloud agents do not inherit local skills or provide an X11 display. In
those environments, first configure the agent runtime and its MCP permissions;
installing the skill file alone is insufficient.

Useful environment variables:

| Variable | Role |
| --- | --- |
| `AGENT_RECORDER_DIR` | Recording root. Default: `~/.agent-recorder` |
| `AGENT_RECORDER_FFMPEG` | Explicit `ffmpeg` binary |
| `FFL_NETWORK_PROFILE` | Optional FFL transport override: `relay`, `p2p`, `direct`, or `synthetic-dns-198-18` |

Recordings are written to `<root>/recordings/rec_YYYYMMDD_HHMMSS_<id>.mp4`.

## Tools

| Tool | Purpose |
| --- | --- |
| `startRecording` | Select this agent's display and start FFmpeg. Defaults: 5 fps, 7200 seconds. Optional `outputDir` writes the file into an existing writable folder. |
| `recordingStatus` | Duration, size, display, and state. `idle` when nothing is active. |
| `finishRecording` | Stop, finalize, and hand the file to a transfer strategy. |
| `confirmUpload` | Store the Google Drive link and apply `after_upload` cleanup. |
| `abortRecording` | Stop without sharing. Deletes the partial file unless `deletePartial` is false. |
| `cleanupRecording` | Delete one local recording by `recordingId` and stop its share. |

`finishRecording` defaults to `delivery=ffl` and `cleanup=after_download`. `delivery=local` with `cleanup=manual` returns a `file:` URI and leaves the file in place. `delivery=google_drive` with `cleanup=after_upload` returns `localPath` for the assistant's Google Drive connector. Pass `outputDir` on `startRecording` as a folder that connector can read, such as `/workspace`. `confirmUpload` stores the Drive URL and then deletes that file.

A second `startRecording` while one recording is active returns that recording and sets `alreadyRecording` to true.

## Display selection

`startRecording` looks at X11 sockets and the process tree that spawned this server (the agent, an intermediate launcher such as `uvx`, and browsers those processes started). It prefers a single browser display in that tree. Otherwise it uses the nearest `DISPLAY` on that chain.

It does not fall back to another socket. If the display cannot be identified, or a frame cannot be grabbed from it, the tool fails with:

```text
No active agent display could be identified.
```

A blank frame on the identified display is still recorded. The browser often opens after recording starts.

## FFL network transport

FFL delivery selects a transport automatically when `finishRecording` shares a recording.
If `FFL_NETWORK_PROFILE` is not set, the server probes DNS for `example.com` and
`stun.cloudflare.com` in parallel, using a total timeout of 0.5 seconds.
When **all** returned addresses for both hosts are in `198.18.0.0/15` (the synthetic DNS
range used by some managed sandbox environments), it calls ffl-python with
`force_relay=True` and `preferred_tunnel="default:web"`.
Otherwise it leaves the existing P2P-first behavior unchanged.

The optional `FFL_NETWORK_PROFILE` setting takes priority over detection:
`relay` forces relay, `p2p` or `direct` keeps P2P, and
`synthetic-dns-198-18` selects the managed-sandbox web relay policy.
Unrecognized non-empty values raise an error rather than silently changing behavior.
The selected profile is cached for the lifetime of the MCP server.
This applies only to FFL shares; local and Google Drive delivery are unchanged.

## Cleanup

Creating an FFL link does not delete the file. With `after_download`, the server waits for FFL's `completed` event (`/transfer/complete`), stops the share, then deletes the local file. That event covers a full HTTP download, including curl, and a WebRTC or direct P2P transfer. If the MCP process exits before that event, the file stays and a later `finishRecording` can share it again.

`maxDurationSeconds` stops FFmpeg and keeps a playable file so `finishRecording` can still share it. A crashed recorder does not leave FFmpeg running past that limit or after its owner process is gone.

## Skill

`skills/agent-session-recording/SKILL.md` is the single recording rule for all supported agents. Its installation paths differ, but every agent should call `startRecording` before browser/computer-use work and `finishRecording` before answering. The skill configures or requests an MCP connector when the tools are unavailable.

## Development

On this machine, tests use the `recoding-mcp` conda environment.

```powershell
conda activate recoding-mcp
pip install -e .
python -m unittest discover -s tests -p "*Test.py" -v
```

`tests/Smoke.py` is a manual check for a Linux agent computer. It records for a few seconds. It does not open a browser; watch the resulting file and confirm it shows the agent display.

```powershell
python tests/Smoke.py --seconds 5 --delivery local --cleanup manual
```

Network share tests are not part of the default suite.

## Out of scope

Dashboard, accounts, tamper-proof storage, action traces, OCR, a custom browser, and Windows/macOS/Wayland capture. This server records, shares, and deletes. Google Drive upload is performed by the assistant's own Drive connector.
