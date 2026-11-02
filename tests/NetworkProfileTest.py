#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

import socket
import threading
import time
import unittest

from agent_recorder.NetworkProfile import FFLNetworkProfile


class NetworkProfileTest(unittest.TestCase):
    @staticmethod
    def _resolver(addressesByHost):
        def resolve(hostname, port, type):
            if port != 443 or type != socket.SOCK_STREAM:
                raise AssertionError("Unexpected DNS probe arguments.")

            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))
                for address in addressesByHost.get(hostname, [])
            ]

        return resolve

    def testSyntheticDNSChoosesWebRelay(self):
        profile = FFLNetworkProfile(
            environ={},
            resolver=self._resolver({
                "example.com": ["198.18.0.1"],
                "stun.cloudflare.com": ["198.19.255.254"],
            }),
        )

        self.assertEqual(profile.shareOptions(), {
            "force_relay": True,
            "preferred_tunnel": "default:web",
        })

    def testMixedOrMissingSyntheticDNSKeepsP2P(self):
        for answers in (
            {"example.com": ["198.18.0.1"], "stun.cloudflare.com": ["1.1.1.1"]},
            {"example.com": ["198.18.0.1"]},
            {"example.com": ["198.18.0.1", "192.0.2.1"], "stun.cloudflare.com": ["198.18.0.2"]},
        ):
            with self.subTest(answers=answers):
                self.assertEqual(
                    FFLNetworkProfile(environ={}, resolver=self._resolver(answers)).shareOptions(),
                    {},
                )

    def testConfiguredProfilesSkipProbing(self):
        def unexpectedProbe(hostname, port, type):
            raise AssertionError("An explicitly configured profile must not probe DNS.")

        expectedOptions = {
            "relay": {"force_relay": True},
            "synthetic-dns-198-18": {"force_relay": True, "preferred_tunnel": "default:web"},
            "p2p": {},
            "direct": {},
        }
        for configured, expected in expectedOptions.items():
            with self.subTest(configured=configured):
                profile = FFLNetworkProfile(
                    environ={"FFL_NETWORK_PROFILE": configured},
                    resolver=unexpectedProbe,
                )
                self.assertEqual(profile.shareOptions(), expected)

    def testInvalidConfiguredProfileFailsFast(self):
        profile = FFLNetworkProfile(environ={"FFL_NETWORK_PROFILE": "invalid"})
        with self.assertRaisesRegex(ValueError, "FFL_NETWORK_PROFILE"):
            profile.shareOptions()

    def testProbeDNSFailuresDoNotSelectRelay(self):
        def unavailable(hostname, port, type):
            raise socket.gaierror("DNS unavailable")

        self.assertEqual(FFLNetworkProfile(environ={}, resolver=unavailable).shareOptions(), {})

    def testSlowDNSProbeHasBoundedWait(self):
        blocked = threading.Event()

        def slow(hostname, port, type):
            blocked.wait(1)
            return []

        started = time.monotonic()
        try:
            profile = FFLNetworkProfile(environ={}, resolver=slow, timeoutSeconds=0.02)
            self.assertEqual(profile.shareOptions(), {})
            self.assertLess(time.monotonic() - started, 0.2)
        finally:
            blocked.set()

    def testProfileCachesResultAndDoesNotExposeItsMutableDict(self):
        calls = []

        def resolve(hostname, port, type):
            calls.append(hostname)
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.1", port))]

        profile = FFLNetworkProfile(environ={}, resolver=resolve)
        first = profile.shareOptions()
        first.clear()
        self.assertTrue(profile.shareOptions()["force_relay"])
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
