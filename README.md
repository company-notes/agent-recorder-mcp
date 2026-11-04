# agent-recorder-mcp

Local MCP server that records the computer an agent is using and returns a replay link when the task is done.

The recording stays on the agent machine. The model receives a link, not the video. FastFileLink is the delivery transport: the local file remains until the recipient finishes downloading.

Version **0.2.3** captures the **agent machine's** Linux X11 display,
not the user's desktop. It works with compatible agents that have access to
their own X11 display and MCP tools. Windows/macOS/Wayland capture is not implemented.

## Install — Skill first, MCP second

**Give the agent the Skill URL, not an MCP install command.** The skill is the
single entry point for installation. It instructs the receiving agent to
install/load the skill, check for the recording tools, register the pinned MCP
connector if needed, and verify tool availability.

**Share this URL:**

```text
https://raw.githubusercontent.com/company-notes/agent-recorder-mcp/v0.2.3/skills/agent-session-recording/SKILL.md
```

[View the versioned SKILL.md on GitHub](https://github.com/company-notes/agent-recorder-mcp/blob/v0.2.3/skills/agent-session-recording/SKILL.md)

An agent receiving only the repository URL should follow the same skill-first
flow, starting from the link above. The common skill source lives at
`skills/agent-session-recording/SKILL.md`. The MCP installer is **not required
to install the skill**. Installing a skill does not automatically give an agent
OS, connector-management or recording permissions: the agent must obtain any
required approvals, and may need a client restart to discover the new tools.

The agent should finish by stating separately whether the skill is installed,
the MCP connector is registered, and `startRecording`, `recordingStatus`,
`finishRecording` are actually available. A missing approval or unsupported
MCP client must be reported as incomplete, not called installed.

### Supported agent integration

| Agent | Skill location | MCP registration |
| --- | --- | --- |
| Grok Bot / Grok Build | `~/.grok/skills/agent-session-recording/SKILL.md` | Grok Bot custom connector / Grok Build config |
| Claude Code | `~/.claude/skills/agent-session-recording/SKILL.md` | CLI/MCP installer |
| Codex | `~/.agents/skills/agent-session-recording/SKILL.md` | MCP installer or TOML config |
| Cursor | `~/.cursor/skills/agent-session-recording/SKILL.md` | MCP JSON config |
| Copilot | `~/.copilot/skills/agent-session-recording/SKILL.md` | Client-specific MCP setup |
| Other agents | Agent's supported skill directory | Client-specific stdio MCP setup |

If a compatible skill manager is available, install the Skill using the URL
above **before** handling the MCP. If the agent can only read the Skill,
it can follow those instructions for the current session, but persistent
skill installation still requires the client's supported mechanism.

The Skill contains specific Grok Bot, Grok Build, Claude, Codex and Cursor
connector setup steps. It pins the MCP source to `v0.2.3`:

```json
{
  "command": "uvx",
  "args": [
    "--from",
    "git+https://github.com/company-notes/agent-recorder-mcp.git@v0.2.3",
    "agent-recorder-mcp"
  ]
}
```

An already-installed local copy of this package also provides
`agent-recorder-mcp install --target claude-code,codex,grok-build` for MCP
registration, and `agent-recorder-mcp install-skill --target all` for copying
the Skill to additional directories. These are **optional helpers**, not
requirements for reading or installing the Skill first. Do not send users
through an MCP-first workflow.

The agent runtime needs Python 3.11+ via `uvx`, `ffmpeg`, and an X11 size
tool (`xdpyinfo` or `xwininfo`, commonly `x11-utils`). MCP approval,
FFL sharing and Drive uploads may require user permission.

Useful environment variables:

| Variable | Role |
| --- | --- |
| `AGENT_RECORDER_DIR` | Recording root. Default: `~/.agent-recorder` |
| `AGENT_RECORDER_FFMPEG` | Explicit `ffmpeg` binary |
| `FFL_NETWORK_PROFILE` | Optional FFL transport override: `relay`, `p2p`, `direct`, or `synthetic-dns-198-18` |

Pass `title` to `startRecording` to name an MP4 using the agent machine's
**local start time**. For example:

```text
2026-11-04_1408_devto-hashnode-github-login.mp4
```

Unsafe filename characters become hyphens. If the same title is used
again within a minute, the MCP appends `-2`, `-3`, etc. and never overwrites
an existing recording. The normalized title is limited to 48 characters.
The `fileName` field in the tool response identifies the actual MP4 name.

For backward compatibility, omitting `title` still generates
`rec_YYYYMMDD_HHMMSS_<id>.mp4`. The default folder is
`<root>/recordings`; `outputDir` can select an existing writable folder.
The **recommended Skill workflow** calls
`finishRecording(package="zip", summaryMarkdown="...")`, which first
finalizes the local MP4, then creates a same-stem `YYYY-MM-DD_HHMM_title.zip`
containing exactly that MP4 and `summary.md`. FFL shares **the ZIP**, not the
original MP4. `after_download` deletes **both the ZIP and MP4** when the
download completes. The `downloadFileName` field reports the shared ZIP name;
`fileName` remains the original MP4 name.

For backward compatibility, `finishRecording()` without `package="zip"`
still shares the original MP4. ZIP packaging currently requires FFL and a
non-empty `summaryMarkdown`; local or Google Drive delivery retains the
existing MP4 behavior.

## Tools

| Tool | Purpose |
| --- | --- |
| `startRecording` | Select this agent's display and start FFmpeg. Defaults: 5 fps, 7200 seconds. Supply `title` to generate a descriptive MP4. Optional `outputDir` writes the file into an existing writable folder. |
| `recordingStatus` | Duration, size, display, and state. `idle` when nothing is active. |
| `finishRecording` | Finalize a recording. Use `package="zip"` with `summaryMarkdown` to share a ZIP containing the MP4 and `summary.md` through FFL; the default `package="video"` preserves legacy behavior. |
| `confirmUpload` | Store the Google Drive link and apply `after_upload` cleanup. |
| `abortRecording` | Stop without sharing. Deletes the partial file unless `deletePartial` is false. |
| `cleanupRecording` | Delete one local recording by `recordingId` and stop its share. |

`finishRecording` defaults to `delivery=ffl` and `cleanup=after_download`. In ZIP mode, both the MP4 and the ZIP remain on disk until FFL's completed-download event triggers cleanup. `delivery=local` with `cleanup=manual` returns a `file:` URI and leaves the MP4 in place. `delivery=google_drive` with `cleanup=after_upload` returns `localPath` for the assistant's Google Drive connector. Pass `outputDir` on `startRecording` as a folder that connector can read, such as `/workspace`. `confirmUpload` stores the Drive URL and then deletes that file.

A second `startRecording` while one recording is active returns that recording and sets `alreadyRecording` to true. Its existing filename is unchanged. The Skill must verify that `startRecording` exposes `title` **and** `finishRecording` exposes `package` and `summaryMarkdown`, upgrading an older MCP when needed.

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

`skills/agent-session-recording/SKILL.md` is the canonical **skill-first installation guide** and recording rule. The user shares this skill, the agent handles its own MCP setup as needed, and the agent verifies that `startRecording` supports `title` before saying setup succeeded. During browser/computer-use work it calls `startRecording(title="...")` before the first UI action and `finishRecording` before answering.

The skill also requires a **recording summary** alongside the ZIP replay URL and inside the ZIP as `summary.md`: the time span and duration, key steps, systems/accounts involved, changes made, human assistance such as 2FA, and errors or detours and their resolutions. Never include passwords, verification codes or key contents. The agent writes this summary from its own recorded actions; the MCP does not analyze the video.

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
