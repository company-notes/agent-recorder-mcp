#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

import tempfile
import unittest
from pathlib import Path

from agent_recorder.Paths import AppPaths
from agent_recorder.SkillInstall import SkillInstaller


class SkillInstallTest(unittest.TestCase):

    def testProjectFilesResolve(self):
        self.assertTrue(AppPaths.installConfig().is_file())
        text = AppPaths.skillSource().read_text(encoding="utf-8")
        self.assertIn("startRecording", text)
        self.assertIn("finishRecording", text)
        self.assertIn("Bootstrap: Skill first, then MCP", text)
        self.assertIn("startRecording", text)
        self.assertIn("Check the MCP tools and version compatibility", text)
        self.assertIn("supports the `title` argument", text)
        self.assertIn("recording summary: the time span and duration", text)
        self.assertIn("Never put passwords,", text)
        self.assertIn("the replay URL and its recording summary", text)
        self.assertIn("v0.2.3", text)
        self.assertIn("startRecording(title=", text)
        self.assertIn("YYYY-MM-DD_HHMM_", text)

    def testInstallCopiesOnceUnlessOverwriteIsSet(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "SKILL.md"
            source.write_text("original", encoding="utf-8")
            installer = SkillInstaller(source, root)
            destinations = installer.install(targets=("grok", "claude", "codex", "cursor", "copilot"))
            self.assertEqual(len(destinations), 5)
            for destination in destinations:
                self.assertEqual(destination.read_text(encoding="utf-8"), "original")

            source.write_text("changed", encoding="utf-8")
            installer.install(targets=("claude",))
            self.assertEqual(installer.destination("claude").read_text(encoding="utf-8"), "original")
            installer.install(targets=("claude",), overwrite=True)
            self.assertEqual(installer.destination("claude").read_text(encoding="utf-8"), "changed")
            self.assertEqual(installer.destination("grok").read_text(encoding="utf-8"), "original")

    def testCustomSkillDirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "SKILL.md"
            source.write_text("shared", encoding="utf-8")
            destination = SkillInstaller(source, root).install(
                targets=(), directory=root / "other-agent" / "skills",
            )
            self.assertEqual(destination, [root / "other-agent" / "skills" / AppPaths.SKILL_NAME / "SKILL.md"])
            self.assertEqual(destination[0].read_text(encoding="utf-8"), "shared")

    def testMCPInstallTargetsOnlyInstallRelevantSkills(self):
        self.assertEqual(SkillInstaller.targetsForMCPArguments([]), ("claude", "codex", "grok"))
        self.assertEqual(
            SkillInstaller.targetsForMCPArguments(["--target", "codex,claude-code,grok-build"]),
            ("codex", "claude", "grok"),
        )
        self.assertEqual(SkillInstaller.targetsForMCPArguments(["--target=claude-desktop"]), ())
        self.assertEqual(SkillInstaller.targetsForMCPArguments(["--target", "codex-cli"]), ("codex",))
        with self.assertRaises(ValueError):
            SkillInstaller.targetsForMCPArguments(["--target", "unknown"])
        with self.assertRaises(ValueError):
            SkillInstaller.targetsForMCPArguments(["--target"])

    def testUnknownSkillTargetFails(self):
        with tempfile.TemporaryDirectory() as directory:
            installer = SkillInstaller(homeDir=Path(directory))
            with self.assertRaises(ValueError):
                installer.destination("unknown")


if __name__ == "__main__":
    unittest.main()
