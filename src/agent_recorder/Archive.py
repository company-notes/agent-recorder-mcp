#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""Package a finished recording and agent-authored Markdown summary for sharing."""

from __future__ import annotations

import pathlib
import zipfile

from agent_recorder.Models import RecorderError


class RecordingArchive:
    MAX_SUMMARY_BYTES = 64 * 1024

    @classmethod
    def validateSummary(cls, summaryMarkdown: str | None) -> str:
        if not isinstance(summaryMarkdown, str) or not summaryMarkdown.strip():
            raise ValueError("ZIP delivery requires a non-empty summaryMarkdown.")

        summary = summaryMarkdown.strip() + "\n"
        if len(summary.encode("utf-8")) > cls.MAX_SUMMARY_BYTES:
            raise ValueError("summaryMarkdown exceeds the 64 KiB limit.")

        return summary

    @classmethod
    def create(cls, videoPath: pathlib.Path, summaryMarkdown: str) -> pathlib.Path:
        """Create a ZIP exclusively; never overwrite a previous archive."""
        summary = cls.validateSummary(summaryMarkdown)
        archivePath = videoPath.with_suffix(".zip")
        created = False
        try:
            with archivePath.open("xb") as output:
                created = True
                with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
                    archive.write(
                        videoPath,
                        arcname=videoPath.name,
                        compress_type=zipfile.ZIP_STORED,
                    )
                    archive.writestr(
                        "summary.md",
                        summary,
                        compress_type=zipfile.ZIP_DEFLATED,
                    )
        except FileExistsError as error:
            raise RecorderError(f"Recording ZIP already exists: {archivePath}") from error
        except Exception:
            if created:
                archivePath.unlink(missing_ok=True)

            raise

        return archivePath
