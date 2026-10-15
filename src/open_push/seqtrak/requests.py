"""Paced Parameter Requests to the Seqtrak, with reply tracking and retries.

The Seqtrak answers every Parameter Request (F0 43 30 7F 1C 0C H M L F7) with a Parameter Change
for the same address, even when there is no value (empty step: no data bytes). Sent all at once, it
drops most of them: on a project load ~1,000 requests got ~200 replies (Pi capture 2026-10-15).

So requests go through this queue: at most `window` wait for a reply at a time, an unanswered one
is sent again after `timeout`, up to `retries` times, and anything that still fails is logged.
"""
import time


class RequestQueue:
    def __init__(self, send=None, window=8, timeout=0.5, retries=3, clock=time.monotonic, log=print):
        self.send = send              # function(address list) that sends the request
        self.window = window
        self.timeout = timeout
        self.retries = retries
        self.clock = clock
        self.log = log
        self.queue = []               # addresses (tuples) waiting to be sent, in order
        self.in_flight = {}           # address -> (time sent, tries so far)
        self.paused_until = 0.0
        self.failed = 0               # requests given up on since start
        self.sent = 0

    def add(self, address):
        """Queue a request (once: an address already queued or waiting isn't added again)."""
        key = tuple(address)
        if key not in self.in_flight and key not in self.queue:
            self.queue.append(key)

    def answered(self, address):
        """A Parameter Change for this address arrived (a reply, or the Seqtrak reporting it)."""
        self.in_flight.pop(tuple(address), None)

    def clear(self):
        """Forget everything pending (e.g. a new project is loading; its re-read follows)."""
        self.queue.clear()
        self.in_flight.clear()

    def pause(self, seconds):
        self.paused_until = max(self.paused_until, self.clock() + seconds)

    def has_room(self):
        """True when nothing is queued and a request could go out now (for low-priority feeders)."""
        return not self.queue and len(self.in_flight) < self.window

    def idle(self):
        return not self.queue and not self.in_flight

    def pump(self):
        """Call often: resend timed-out requests, then send queued ones while there is room."""
        now = self.clock()
        if now < self.paused_until:
            return
        for key, (sent_at, tries) in list(self.in_flight.items()):
            if now - sent_at < self.timeout:
                continue
            if tries <= self.retries:
                self._send(key, tries + 1, now)
            else:
                del self.in_flight[key]
                self.failed += 1
                self.log(f"Seqtrak: no reply to {' '.join(f'{b:02X}' for b in key)} after {tries} tries")
        while self.queue and len(self.in_flight) < self.window:
            self._send(self.queue.pop(0), 1, now)

    def _send(self, key, tries, now):
        self.in_flight[key] = (now, tries)
        self.sent += 1
        if self.send:
            self.send(list(key))
