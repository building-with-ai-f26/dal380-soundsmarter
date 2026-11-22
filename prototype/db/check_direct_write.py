"""Checks that a signed-in user can NOT add rows to the database directly.

This is the proof that migration 002 worked: it signs in as a real user (the
way the browser does, with the public key) and tries to write a prompt event
and a recording straight to Supabase, skipping our server. Both must be refused.

Run from prototype/ (uses the project in the repo-root .env, i.e. dev):
  uv run python db/check_direct_write.py
It asks for a test account's email and password. Nothing is printed or stored
except the result.
"""

import getpass
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")
URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]

ROWS = {
    "prompt_events": {"prompt_id": "des-t-01", "event": "sent"},
    "recordings": {
        "prompt_id": "des-t-01", "family": "describe", "mode": "text", "variant": "place",
        "session_no": 1, "position_in_session": 1, "prep_from": "reveal",
        "metrics": {"total": 0, "fake": True}, "metrics_version": 1, "word_list_version": 1,
        "transcription": {"fake": True}, "stt_model": "none",
    },
}


def main():
    email = input("Test account email: ").strip()
    password = getpass.getpass("Password (hidden as you type): ")
    with httpx.Client(timeout=20) as c:
        r = c.post(URL + "/auth/v1/token?grant_type=password", headers={"apikey": KEY},
                   json={"email": email, "password": password})
        if r.status_code != 200:
            sys.exit("Could not sign in. Check the email and password.")
        session = r.json()
        headers = {"apikey": KEY, "Authorization": "Bearer " + session["access_token"]}
        ok = True
        for table, row in ROWS.items():
            for label, body in (("no user id", row), ("own user id", {**row, "user_id": session["user"]["id"]})):
                r = c.post(f"{URL}/rest/v1/{table}", headers=headers, json=body)
                refused = r.status_code in (401, 403)
                ok = ok and refused
                print(f"{'REFUSED' if refused else 'NOT REFUSED'}  {table} ({label}): HTTP {r.status_code}")
    print("\nPASS: a signed-in user cannot write directly." if ok
          else "\nFAIL: a direct write was not refused. Tell pi.")


if __name__ == "__main__":
    main()
