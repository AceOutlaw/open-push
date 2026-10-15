"""Which Seqtrak values the bridge knows to be current.

The Push mirrors the Seqtrak, but a mirrored value can be old: after a project switch or a reconnect
every project value is stale until the Seqtrak answers again, and a request can go unanswered.
SyncState keeps a quality for each value the Push relies on (keyed by its SysEx address), so the
display can say "syncing" instead of presenting an old value as the device's.

Qualities: unknown (never read) · stale (read before the current project/connection) ·
confirmed (read or reported since) · failed (no reply after retries).
"""

UNKNOWN, STALE, CONFIRMED, FAILED = "unknown", "stale", "confirmed", "failed"
SYNCED, SYNCING, PARTIAL = "synced", "syncing", "partial"


class SyncState:
    def __init__(self):
        self.epoch = 0          # advances on every project load / reconnect
        self.fields = {}        # address tuple -> quality
        self.essential = set()  # addresses that must be confirmed before the Push counts as synced

    def begin(self, essential):
        """A new project or connection: every value read so far is stale until read again."""
        self.epoch += 1
        for key, quality in self.fields.items():
            if quality == CONFIRMED:
                self.fields[key] = STALE
        self.essential = {tuple(a) for a in essential}
        for key in self.essential:
            if self.fields.get(key) in (None, FAILED):
                self.fields[key] = UNKNOWN

    def confirm(self, address):
        self.fields[tuple(address)] = CONFIRMED

    def failed(self, address):
        key = tuple(address)
        if self.fields.get(key) != CONFIRMED:
            self.fields[key] = FAILED

    def quality(self, address):
        return self.fields.get(tuple(address), UNKNOWN)

    def status(self):
        """synced: every essential value confirmed · partial: some failed, none still waiting ·
        syncing: still waiting for some."""
        qualities = [self.fields.get(k, UNKNOWN) for k in self.essential]
        if all(q == CONFIRMED for q in qualities):
            return SYNCED
        if any(q in (UNKNOWN, STALE) for q in qualities):
            return SYNCING
        return PARTIAL
