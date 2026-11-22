"""Checks that a signed-in user can NOT add rows to the database directly.

This is the proof that migration 002 worked: it signs in as a real user (the
way the browser does, with the public key) and tries to write a prompt event
and a recording straight to Supabase, skipping our server. Both must be refused.

Run from prototype/:
  uv run python db/check_direct_write.py          the dev project (repo-root .env)
  uv run python db/check_direct_write.py --prod   the prod project; it asks for
                                                  prod's URL and publishable key
                                                  (both are public; copy them from Render)

It asks for a test account's email and password. If the account doesn't exist
yet, it offers to create it with a sign-up code (add one to that project's
signup_codes table first). Nothing is printed or stored except the result.
"""

import getpass
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from server import CONSENT_VERSION  # noqa: E402  (the consent wording version a new account agrees to)

ROWS = {
    "prompt_events": {"prompt_id": "des-t-01", "event": "sent"},
    "recordings": {
        "prompt_id": "des-t-01", "family": "describe", "mode": "text", "variant": "place",
        "session_no": 1, "position_in_session": 1, "prep_from": "reveal",
        "metrics": {"total": 0, "fake": True}, "metrics_version": 1, "word_list_version": 1,
        "transcription": {"fake": True}, "stt_model": "none",
    },
}


def project(prod: bool) -> tuple[str, str, str]:
    """Which Supabase project to test: (name, url, publishable key)."""
    if not prod:
        load_dotenv(Path(__file__).parent.parent.parent / ".env")
        return "dev", os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_PUBLISHABLE_KEY"]
    url = input("Prod SUPABASE_URL: ").strip().rstrip("/")
    key = input("Prod SUPABASE_PUBLISHABLE_KEY: ").strip()
    if not key.startswith("sb_publishable_"):
        sys.exit("That is not a publishable key (it should start with sb_publishable_). "
                 "Never paste the secret key here. Stopped.")
    return "prod", url, key


def sign_in(c: httpx.Client, url: str, key: str) -> dict:
    email = input("Test account email: ").strip()
    password = getpass.getpass("Password (hidden as you type): ")
    r = c.post(url + "/auth/v1/token?grant_type=password", headers={"apikey": key},
               json={"email": email, "password": password})
    if r.status_code == 200:
        return r.json()
    code = input("Could not sign in. To create this account, type a sign-up code "
                 "(or press Enter to stop): ").strip()
    if not code:
        sys.exit("Stopped. Check the email and password.")
    r = c.post(url + "/auth/v1/signup", headers={"apikey": key}, json={
        "email": email, "password": password,
        "data": {"signup_code": code, "consent_version": CONSENT_VERSION}})
    if r.status_code == 200 and r.json().get("access_token"):
        print("Account created.")
        return r.json()
    sys.exit("Could not create the account. The code may be wrong or already used, "
             "or the email already has an account with a different password.")


def main():
    name, url, key = project("--prod" in sys.argv)
    print(f"Testing the {name} project.")
    with httpx.Client(timeout=20) as c:
        session = sign_in(c, url, key)
        headers = {"apikey": key, "Authorization": "Bearer " + session["access_token"]}
        ok = True
        for table, row in ROWS.items():
            for label, body in (("no user id", row), ("own user id", {**row, "user_id": session["user"]["id"]})):
                r = c.post(f"{url}/rest/v1/{table}", headers=headers, json=body)
                refused = r.status_code in (401, 403)
                ok = ok and refused
                print(f"{'REFUSED' if refused else 'NOT REFUSED'}  {table} ({label}): HTTP {r.status_code}")
    if ok:
        print(f"\nPASS: on {name}, a signed-in user cannot write directly.")
    else:
        print(f"\nFAIL: on {name}, a direct write was not refused. Tell pi. If any line shows HTTP 201, "
              "a fake row was saved: delete it in Supabase's Table Editor (its metrics say \"fake\").")


if __name__ == "__main__":
    main()
