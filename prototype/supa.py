"""Talks to Supabase (sign-in + database) for signed-in users.

Everything goes through Supabase's two web APIs with plain HTTP (httpx), no SDK:
  - Auth  (/auth/v1/...): sign up, sign in, refresh, "who is this token?"
  - REST  (/rest/v1/<table>): read and add rows

Reads carry the *user's own* access token, so row-level security (RLS) in the
database decides what they can see. Writes are different: users cannot add
rows themselves (migration 002). Only this server can, using Supabase's secret
key, and only after it has checked who the user is. That way a stored
recording is always one this server measured.

Settings (repo-root .env locally = the DEV project; Render = the PROD project):
  SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY  (public by design)
  SUPABASE_SECRET_KEY                     (server only; bypasses RLS; never in the browser or git)
"""

import os

import httpx


class SupaError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Supa:
    def __init__(self, url: str, key: str, transport: httpx.AsyncBaseTransport | None = None, secret: str = ""):
        self.url = (url or "").rstrip("/")
        self.key = key or ""
        self.secret = secret or ""  # server-only key for writes
        self.transport = transport  # tests pass a fake one; None = real network

    @classmethod
    def from_env(cls):
        return cls(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_PUBLISHABLE_KEY", ""),
                   secret=os.getenv("SUPABASE_SECRET_KEY", ""))

    @property
    def configured(self) -> bool:
        return bool(self.url and self.key)

    @property
    def can_write(self) -> bool:
        return bool(self.configured and self.secret)

    def _headers(self, token: str | None = None) -> dict:
        h = {"apikey": self.key}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    async def _call(self, method, path, token=None, **kw) -> httpx.Response:
        if not self.configured:
            raise SupaError(503, "Accounts are not set up on this server.")
        headers = {**self._headers(token), **kw.pop("headers", {})}
        async with httpx.AsyncClient(timeout=20, transport=self.transport) as c:
            try:
                return await c.request(method, self.url + path, headers=headers, **kw)
            except httpx.HTTPError:
                raise SupaError(502, "Could not reach the account service.")

    # ---------------- auth ----------------

    @staticmethod
    def _session(data: dict) -> dict:
        """Keep only what the browser needs from a Supabase session."""
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": data.get("expires_in", 3600),
            "email": (data.get("user") or {}).get("email", ""),
        }

    async def sign_up(self, email: str, password: str, signup_code: str, consent_version: str) -> dict:
        # The database refuses the account unless the code is valid and unused
        # and consent is present (trigger in db/migrations/001_init.sql).
        r = await self._call("POST", "/auth/v1/signup", json={
            "email": email, "password": password,
            "data": {"signup_code": signup_code, "consent_version": consent_version},
        })
        if r.status_code == 200 and r.json().get("access_token"):
            return self._session(r.json())
        body = r.text.lower()
        if "already registered" in body or "already been registered" in body or "user_already_exists" in body:
            raise SupaError(409, "An account with that email already exists. Sign in instead.")
        if "password" in body and r.status_code in (400, 422):
            raise SupaError(400, "Password too short or too weak. Use at least 8 characters.")
        if "database error" in body or r.status_code == 500:
            raise SupaError(403, "That sign-up code isn't valid or has already been used.")
        if r.status_code == 200:  # account made but no session: email confirmation is on
            raise SupaError(500, "Account created, but email confirmation is on in Supabase. Turn it off.")
        raise SupaError(400, "Couldn't create the account.")

    async def sign_in(self, email: str, password: str) -> dict:
        r = await self._call("POST", "/auth/v1/token?grant_type=password", json={"email": email, "password": password})
        if r.status_code == 200:
            return self._session(r.json())
        raise SupaError(401, "Email or password is wrong.")

    async def refresh(self, refresh_token: str) -> dict:
        r = await self._call("POST", "/auth/v1/token?grant_type=refresh_token", json={"refresh_token": refresh_token})
        if r.status_code == 200:
            return self._session(r.json())
        raise SupaError(401, "Signed out. Please sign in again.")

    async def user(self, token: str) -> dict:
        """Who does this access token belong to? Raises 401 if it's invalid or expired."""
        r = await self._call("GET", "/auth/v1/user", token)
        if r.status_code == 200:
            return r.json()
        raise SupaError(401, "Signed out. Please sign in again.")

    # ---------------- database (as the user; RLS applies) ----------------

    async def select(self, token: str, table: str, params: dict) -> list[dict]:
        r = await self._call("GET", f"/rest/v1/{table}", token, params=params)
        if r.status_code == 200:
            return r.json()
        raise SupaError(502, f"Database read failed ({table}, {r.status_code}).")

    # ---------------- stimulus files (public Storage bucket 'stimuli') ----------------

    def file_url(self, path: str) -> str:
        """The public address of a stimulus file. Anyone with the link can view it."""
        return f"{self.url}/storage/v1/object/public/stimuli/{path}"

    async def file_exists(self, path: str) -> bool:
        r = await self._call("HEAD", f"/storage/v1/object/public/stimuli/{path}")
        return r.status_code == 200

    # ---------------- database (as the server; bypasses RLS) ----------------

    async def check_can_write(self) -> None:
        """Make sure the secret key really works, before anything is paid for.

        Sends an empty recording, which the database always turns down because
        required fields are missing, so no row is ever created. What matters
        is *why* it was turned down: 401 or 403 means the key is wrong, revoked
        or not allowed to add rows (migration 003 not run).
        """
        if not self.can_write:
            raise SupaError(503, "Saving is not set up on this server.")
        r = await self._call("POST", "/rest/v1/recordings", json={}, headers={
            "apikey": self.secret, "Authorization": f"Bearer {self.secret}", "Prefer": "return=minimal"})
        if r.status_code in (401, 403):
            raise SupaError(503, "Saving isn't working on this server right now. Nothing was sent for analysis.")

    async def insert_as_server(self, table: str, row: dict) -> None:
        """Add a row with the secret key. The caller must put a verified user_id in the row.

        The secret key is only allowed to add rows to prompt_events and recordings
        (migration 003), not read them, so we ask for nothing back.
        """
        if not self.can_write:
            raise SupaError(503, "Saving is not set up on this server.")
        r = await self._call("POST", f"/rest/v1/{table}", json=row, headers={
            "apikey": self.secret, "Authorization": f"Bearer {self.secret}", "Prefer": "return=minimal"})
        if r.status_code == 201:
            return
        raise SupaError(502, f"Database write failed ({table}, {r.status_code}).")
