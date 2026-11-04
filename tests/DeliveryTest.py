#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

import socket
import tempfile
import unittest
from pathlib import Path

from agent_recorder.Delivery import FFLDelivery, GoogleDriveDelivery, LocalDelivery
from agent_recorder.Models import DeliveryError
from agent_recorder.NetworkProfile import FFLNetworkProfile

from Support import sampleRecording


class _Session:
    def __init__(self, link, captured):
        self.link = link
        self.captured = captured
        self.closed = False

    def close(self):
        self.closed = True


def _share(path, **kwargs):
    session = _Session("https://fastfilelink.example/abc", {"path": path, "kwargs": kwargs})
    return session


class DeliveryTest(unittest.TestCase):

    def testFflShareReturnsTheSessionLink(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = sampleRecording(Path(directory))
            profile = FFLNetworkProfile(environ={"FFL_NETWORK_PROFILE": "p2p"})
            result = FFLDelivery(_share, profile).deliver(recording)
            self.assertEqual(result.url, "https://fastfilelink.example/abc")
            self.assertEqual(result.session.captured["path"], str(recording.outputPath))
            self.assertEqual(result.session.captured["kwargs"], {"name": recording.outputPath.name})
            self.assertFalse(result.session.closed)

    def testFflSharePassesTheTitledFilenameToTheReceiver(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outputPath = root / "recordings" / "2026-11-04_1408_github-login.mp4"
            recording = sampleRecording(root, outputPath=outputPath)
            profile = FFLNetworkProfile(environ={"FFL_NETWORK_PROFILE": "p2p"})
            result = FFLDelivery(_share, profile).deliver(recording)

            self.assertEqual(result.session.captured["path"], str(outputPath))
            self.assertEqual(
                result.session.captured["kwargs"]["name"],
                "2026-11-04_1408_github-login.mp4",
            )

    def testFflSharesZipWhenArchiveExists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recording = sampleRecording(
                root,
                archivePath=root / "recordings" / "2026-11-04_1408_github-login.zip",
            )
            profile = FFLNetworkProfile(environ={"FFL_NETWORK_PROFILE": "p2p"})
            result = FFLDelivery(_share, profile).deliver(recording)
            self.assertEqual(
                result.session.captured["path"],
                str(recording.archivePath),
            )
            self.assertEqual(
                result.session.captured["kwargs"]["name"],
                "2026-11-04_1408_github-login.zip",
            )

    def testFflShareWithoutALinkFails(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = sampleRecording(Path(directory))
            session = _Session("", {})

            def share(path, **kwargs):
                del path, kwargs
                return session

            with self.assertRaises(DeliveryError):
                profile = FFLNetworkProfile(environ={"FFL_NETWORK_PROFILE": "p2p"})
                FFLDelivery(share, profile).deliver(recording)

            self.assertTrue(session.closed)

    def testFflDeliveryAutoSelectsRelayForSyntheticDNS(self):
        def resolve(hostname, port, type):
            del hostname, type
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.1", port))]

        with tempfile.TemporaryDirectory() as directory:
            recording = sampleRecording(Path(directory))
            profile = FFLNetworkProfile(environ={}, resolver=resolve)
            result = FFLDelivery(_share, profile).deliver(recording)

            self.assertEqual(result.session.captured["kwargs"], {
                "name": recording.outputPath.name,
                "force_relay": True,
                "preferred_tunnel": "default:web",
            })

    def testFflDeliveryHonorsConfiguredRelay(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = sampleRecording(Path(directory))
            profile = FFLNetworkProfile(environ={"FFL_NETWORK_PROFILE": "relay"})
            result = FFLDelivery(_share, profile).deliver(recording)

            self.assertEqual(result.session.captured["kwargs"], {
                "name": recording.outputPath.name,
                "force_relay": True,
            })

    def testLocalDeliveryReturnsAFileUri(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = sampleRecording(Path(directory))
            result = LocalDelivery().deliver(recording)
            self.assertTrue(result.url.startswith("file:"))
            self.assertIsNone(result.session)

    def testGoogleDriveDeliveryWaitsForTheConnector(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = sampleRecording(Path(directory))
            result = GoogleDriveDelivery().deliver(recording)
            self.assertIsNone(result.url)
            self.assertTrue(result.awaitsUpload)
            self.assertIsNone(result.session)


if __name__ == "__main__":
    unittest.main()
