#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0

"""Select FFL's share transport from the agent machine's network environment."""

from __future__ import annotations

import ipaddress
import logging
import os
import queue
import socket
import threading
import time

from collections.abc import Mapping
from typing import Callable


logger = logging.getLogger(__name__)


class FFLNetworkProfile:
    PROFILE_ENV_KEY = "FFL_NETWORK_PROFILE"
    SYNTHETIC_DNS_PROFILE = "synthetic-dns-198-18"
    SYNTHETIC_DNS_NETWORK = ipaddress.ip_network("198.18.0.0/15")
    PROBE_HOSTNAMES = ("example.com", "stun.cloudflare.com")
    PROBE_TIMEOUT_SECONDS = 0.5

    def __init__(
        self,
        environ: Mapping[str, str] | None = None,
        resolver: Callable | None = None,
        timeoutSeconds: float = PROBE_TIMEOUT_SECONDS,
    ):
        if timeoutSeconds <= 0:
            raise ValueError("timeoutSeconds must be positive.")

        self._environ = os.environ if environ is None else environ
        self._resolver = socket.getaddrinfo if resolver is None else resolver
        self._timeoutSeconds = timeoutSeconds
        self._shareOptions: dict | None = None

    @classmethod
    def _isSyntheticAddress(cls, address: str) -> bool:
        try:
            return ipaddress.ip_address(address) in cls.SYNTHETIC_DNS_NETWORK
        except ValueError:
            return False

    def _resolveHost(self, hostname: str, completed: queue.Queue) -> None:
        try:
            records = self._resolver(hostname, 443, type=socket.SOCK_STREAM)
            addresses = {record[4][0] for record in records}
        except OSError as error:
            logger.debug("FFL network probe for %s failed: %s", hostname, error)
            addresses = set()
        except Exception as error:
            completed.put((hostname, error))
            return

        completed.put((hostname, addresses))

    def _hasSyntheticDNS(self) -> bool:
        completed = queue.Queue()
        deadline = time.monotonic() + self._timeoutSeconds
        results = {}

        for hostname in self.PROBE_HOSTNAMES:
            threading.Thread(
                target=self._resolveHost,
                args=(hostname, completed),
                daemon=True,
            ).start()

        while len(results) < len(self.PROBE_HOSTNAMES):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.debug("FFL network profile probe timed out.")
                return False

            try:
                hostname, addresses = completed.get(timeout=remaining)
            except queue.Empty:
                logger.debug("FFL network profile probe timed out.")
                return False

            if isinstance(addresses, Exception):
                raise addresses

            results[hostname] = addresses

        return all(
            results[hostname]
            and all(self._isSyntheticAddress(address) for address in results[hostname])
            for hostname in self.PROBE_HOSTNAMES
        )

    def shareOptions(self) -> dict:
        """Use the same managed-sandbox relay policy as ffl-mcp."""
        if self._shareOptions is not None:
            return dict(self._shareOptions)

        configured = self._environ.get(self.PROFILE_ENV_KEY, "").strip().lower()
        if configured in ("p2p", "direct"):
            options = {}
        elif configured == "relay":
            options = {"force_relay": True}
        elif configured == self.SYNTHETIC_DNS_PROFILE or (
            not configured and self._hasSyntheticDNS()
        ):
            options = {"force_relay": True, "preferred_tunnel": "default:web"}
        elif configured:
            raise ValueError(f"Unsupported {self.PROFILE_ENV_KEY}: {configured}")
        else:
            options = {}

        self._shareOptions = options
        if options:
            logger.info("Using FFL relay for recording delivery.")

        return dict(options)
