#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

import tempfile
import unittest
import zipfile

from pathlib import Path
from unittest.mock import patch

from agent_recorder.Archive import RecordingArchive
from agent_recorder.Models import RecorderError


class ArchiveTest(unittest.TestCase):

    def testZipContainsNamedVideoAndSummaryMarkdown(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "2026-11-04_1408_github-login.mp4"
            video.write_bytes(b"example video bytes")
            summary = "# Summary\n\n1. Signed in to GitHub using user-assisted 2FA."
            path = RecordingArchive.create(video, summary)
            self.assertEqual(path.name, "2026-11-04_1408_github-login.zip")
            with zipfile.ZipFile(path) as archive:
                self.assertEqual(
                    sorted(archive.namelist()),
                    ["2026-11-04_1408_github-login.mp4", "summary.md"],
                )
                self.assertEqual(archive.read(video.name), b"example video bytes")
                self.assertEqual(archive.read("summary.md").decode("utf-8"), summary + "\n")

            self.assertEqual(video.read_bytes(), b"example video bytes")

    def testUnicodeSummaryAndVideoName(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "2026-11-04_1408_登入-測試.mp4"
            video.write_bytes(b"recording")
            path = RecordingArchive.create(video, "登入時需要使用者協助完成雙重驗證。")
            with zipfile.ZipFile(path) as archive:
                self.assertIn(video.name, archive.namelist())
                self.assertIn("雙重驗證", archive.read("summary.md").decode("utf-8"))

    def testArchiveExistsDoesNotOverwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "capture.mp4"
            video.write_bytes(b"recording")
            archive = video.with_suffix(".zip")
            archive.write_bytes(b"preserve this")
            with self.assertRaises(RecorderError):
                RecordingArchive.create(video, "# Summary")

            self.assertEqual(archive.read_bytes(), b"preserve this")

    def testInvalidMarkdownRejectedBeforeCreatingArchive(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "capture.mp4"
            video.write_bytes(b"recording")
            for summary in (None, "", "   ", 123, "x" * (RecordingArchive.MAX_SUMMARY_BYTES + 1)):
                with self.subTest(summary=str(summary)[:12]), self.assertRaises(ValueError):
                    RecordingArchive.create(video, summary)

            self.assertFalse(video.with_suffix(".zip").exists())

    def testFailedZipWriteRemovesPartialZipButPreservesVideo(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "capture.mp4"
            video.write_bytes(b"keep video")
            with patch.object(zipfile.ZipFile, "write", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    RecordingArchive.create(video, "summary")

            self.assertEqual(video.read_bytes(), b"keep video")
            self.assertFalse(video.with_suffix(".zip").exists())


if __name__ == "__main__":
    unittest.main()
