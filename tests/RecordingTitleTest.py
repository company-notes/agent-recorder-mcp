#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

import unittest

from agent_recorder.Models import RecordingTitle


class RecordingTitleTest(unittest.TestCase):

    def testSlugNormalizesUnsafeCharacters(self):
        self.assertEqual(
            RecordingTitle.slug(" Dev.to / Hashnode GitHub Login! "),
            "dev-to-hashnode-github-login",
        )
        self.assertEqual(RecordingTitle.slug("登入 GitHub 帳號"), "登入-github-帳號")
        self.assertEqual(RecordingTitle.slug("ＡＢＣ __ 123"), "abc-123")

    def testSlugDoesNotAllowTraversal(self):
        self.assertEqual(RecordingTitle.slug("../../secret"), "secret")
        self.assertEqual(RecordingTitle.slug("foo\\bar"), "foo-bar")

    def testSlugIsBoundedToAFilesystemSafeLength(self):
        slug = RecordingTitle.slug("錄" * 100)
        self.assertEqual(slug, "錄" * RecordingTitle.MAX_SLUG_LENGTH)
        self.assertLessEqual(len(slug.encode("utf-8")), 192)

    def testSlugRejectsInvalidOrEmptyTitles(self):
        for value in ("", " ", "...///\\", "✨", None, 123, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RecordingTitle.slug(value)


if __name__ == "__main__":
    unittest.main()
