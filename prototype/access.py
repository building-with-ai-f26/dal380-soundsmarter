"""Access gate for the shared demo: invite codes + a daily cap.

Protects the Deepgram bill when the app is online. Each invite code gets a few
takes; all codes together share a daily cap. Counts live in memory, so they
reset if the server restarts (fine for a demo; the daily cap still holds).

Settings come from environment variables (never hard-coded):
  ACCESS_CODES    comma-separated invite codes, e.g. "ABC123,DEF456"
  TAKES_PER_CODE  takes allowed per code (default 3)
  DAILY_CAP       total takes per day across all codes (default 30)

If ACCESS_CODES is empty: open when running locally, locked when running on
Render (Render sets RENDER=true), so a forgotten setting fails safe.
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


class AccessDenied(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Gate:
    def __init__(self, codes, takes_per_code=3, daily_cap=30, on_server=False, today=None):
        self.codes = {c.strip().upper() for c in codes if c.strip()}
        self.takes_per_code = takes_per_code
        self.daily_cap = daily_cap
        self.on_server = on_server
        self._today = today or (lambda: datetime.now(NY).date())
        self.used = {}  # code -> takes used
        self.day = None
        self.today_count = 0

    @classmethod
    def from_env(cls):
        return cls(
            codes=os.getenv("ACCESS_CODES", "").split(","),
            takes_per_code=int(os.getenv("TAKES_PER_CODE", "3")),
            daily_cap=int(os.getenv("DAILY_CAP", "30")),
            on_server=bool(os.getenv("RENDER")),
        )

    def _roll_day(self):
        if self.day != self._today():
            self.day = self._today()
            self.today_count = 0

    def _check(self, code):
        """Return the normalized code, or raise AccessDenied."""
        if not self.codes:
            if self.on_server:
                raise AccessDenied(503, "The demo is not open right now.")
            return None  # local, no codes set: open
        code = (code or "").strip().upper()
        if code not in self.codes:
            raise AccessDenied(403, "This link needs a valid invite code.")
        if self.used.get(code, 0) >= self.takes_per_code:
            raise AccessDenied(429, "You've used all your takes. Thanks for trying SoundSmarter!")
        self._roll_day()
        if self.today_count >= self.daily_cap:
            raise AccessDenied(429, "The demo is full for today. Please try again tomorrow.")
        return code

    def takes_left(self, code):
        """How many takes this code has left (raises AccessDenied if none)."""
        code = self._check(code)
        if code is None:
            return None  # unlimited locally
        return self.takes_per_code - self.used.get(code, 0)

    def reserve(self, code):
        """Use up one take before calling Deepgram. Returns a token for refund()."""
        code = self._check(code)
        if code is not None:
            self.used[code] = self.used.get(code, 0) + 1
            self.today_count += 1
        return code

    def refund(self, code):
        """Give the take back if Deepgram failed (we weren't charged)."""
        if code is not None:
            self.used[code] -= 1
            self.today_count -= 1
