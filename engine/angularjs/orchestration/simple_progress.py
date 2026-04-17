import sys
import time

class SimpleProgress:
    def __init__(self, total, label=""):
        self.total = max(total, 1)
        self.current = 0
        self.label = label
        self.start = time.time()

    def step(self, msg=""):
        self.current += 1
        percent = int((self.current / self.total) * 100)

        elapsed = time.time() - self.start
        rate = self.current / elapsed if elapsed > 0 else 0
        eta = int((self.total - self.current) / rate) if rate > 0 else 0

        bar_len = 20
        filled = int(bar_len * self.current / self.total)
        bar = "=" * filled + ">" + " " * (bar_len - filled)

        sys.stdout.write(
            f"\r[{bar}] {percent}% | {self.label} | {msg} | ETA: {eta}s"
        )
        sys.stdout.flush()

    def done(self):
        print()