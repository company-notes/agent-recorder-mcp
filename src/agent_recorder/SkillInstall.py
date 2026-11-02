#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
import os
import pathlib

from collections.abc import Sequence

from agent_recorder.Paths import AppPaths


logger = logging.getLogger(__name__)


class SkillInstaller:
    """Install the same bundled skill into supported agent skill directories."""

    TARGET_DIRS = {
        "grok": ".grok",
        "claude": ".claude",
        "codex": ".agents",
        "cursor": ".cursor",
        "copilot": ".copilot",
    }
    MCP_TARGET_SKILLS = {
        "claude-desktop": (),
        "claude-code": ("claude",),
        "codex": ("codex",),
        "grok-build": ("grok",),
        "all": ("claude", "codex", "grok"),
    }
    MCP_TARGET_ALIASES = {
        "claude-cli": "claude-code",
        "codex-cli": "codex",
        "codex-desktop": "codex",
        "grok": "grok-build",
    }

    def __init__(
        self,
        sourcePath: pathlib.Path | None = None,
        homeDir: pathlib.Path | None = None,
    ):
        self._sourcePath = sourcePath if sourcePath is not None else AppPaths.skillSource()
        self._homeDir = homeDir if homeDir is not None else pathlib.Path.home()

    @classmethod
    def targetsForMCPArguments(cls, arguments: Sequence[str]) -> tuple[str, ...]:
        """Map the MCP connector installer targets to skill-capable agents."""
        targetValue = "all"
        for index, argument in enumerate(arguments):
            if argument == "--target":
                if index + 1 >= len(arguments):
                    raise ValueError("--target requires a value.")
                targetValue = arguments[index + 1]
            elif argument.startswith("--target="):
                targetValue = argument.partition("=")[2]

        targets = []
        for value in targetValue.split(","):
            name = cls.MCP_TARGET_ALIASES.get(value.strip(), value.strip())
            if name not in cls.MCP_TARGET_SKILLS:
                raise ValueError(f"Unsupported MCP target: {name}")
            for target in cls.MCP_TARGET_SKILLS[name]:
                if target not in targets:
                    targets.append(target)

        return tuple(targets)

    def destination(self, target: str) -> pathlib.Path:
        if target not in self.TARGET_DIRS:
            raise ValueError(f"Unsupported skill target: {target}")

        if target == "grok" and self._homeDir == pathlib.Path.home():
            configured = os.environ.get("GROK_HOME")
            if configured:
                return pathlib.Path(configured).expanduser() / "skills" / AppPaths.SKILL_NAME / "SKILL.md"

        return self._homeDir / self.TARGET_DIRS[target] / "skills" / AppPaths.SKILL_NAME / "SKILL.md"

    def install(
        self,
        targets: Sequence[str] = ("grok", "claude", "codex", "cursor", "copilot"),
        overwrite: bool = False,
        directory: pathlib.Path | None = None,
    ) -> list[pathlib.Path]:
        """Copy one skill source to selected agents or a custom skills root."""
        destinations = [self.destination(target) for target in targets]
        if directory is not None:
            destinations.append(directory.expanduser() / AppPaths.SKILL_NAME / "SKILL.md")

        if not destinations:
            return []

        source = self._sourcePath
        if not source.is_file():
            raise FileNotFoundError(f"Skill source was not found: {source}")

        contents = source.read_text(encoding="utf-8")
        installed = []
        for destination in dict.fromkeys(destinations):
            if destination.is_file() and not overwrite:
                logger.info("Skill already installed at %s", destination)
                installed.append(destination)
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(contents, encoding="utf-8")
            logger.info("Installed skill at %s", destination)
            installed.append(destination)

        return installed
