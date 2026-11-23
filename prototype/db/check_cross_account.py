"""Checks that one signed-in user can NOT read another user's data.

The access-control test for the Build 3 security audit: sign in as Account A
and note what it owns, then sign in as Account B and ask Supabase directly
(the way an attacker would, with the public key and B's own sign-in) for A's
rows. Every answer must come back empty. It only reads stored data; it never
changes or deletes a row. (If Account B doesn't exist, it offers to create it,
which uses up one sign-up code.)

Run from prototype/:
  uv run python db/check_cross_account.py          the dev project (repo-root .env)
  uv run python db/check_cross_account.py --prod   the prod project; it asks for
                                                   prod's URL and publishable key
                                                   (both are public; copy them from Render)

Account A should have at least one recording, or the test proves little.
Account B can be new: if it doesn't exist, the script offers to create it with
a sign-up code. No email, password or stored data is printed, only counts.
"""

import sys

import httpx

from check_direct_write import project, sign_in

TABLES = ("recordings", "prompt_events", "consents")


def rows(c: httpx.Client, url: str, headers: dict, table: str, params: dict) -> tuple[int, list]:
    r = c.get(f"{url}/rest/v1/{table}", headers=headers, params=params)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else []
    return r.status_code, body if isinstance(body, list) else []


def main():
    name, url, key = project("--prod" in sys.argv)
    print(f"Testing the {name} project.\n")
    with httpx.Client(timeout=20) as c:
        print("Account A (the account whose data is being protected)")
        a = sign_in(c, url, key)
        print("\nAccount B (the account trying to read A's data)")
        b = sign_in(c, url, key)
        a_id, b_id = a["user"]["id"], b["user"]["id"]
        if a_id == b_id:
            sys.exit("A and B are the same account. Use two different accounts.")
        a_head = {"apikey": key, "Authorization": "Bearer " + a["access_token"]}
        b_head = {"apikey": key, "Authorization": "Bearer " + b["access_token"]}

        print("\nWhat Account A can see of its own data:")
        a_counts, a_recording = {}, None
        for table in TABLES:
            _, own = rows(c, url, a_head, table, {"select": "*", "user_id": f"eq.{a_id}"})
            a_counts[table] = len(own)
            if table == "recordings" and own:
                a_recording = own[0]["id"]
            print(f"  {table}: {len(own)} rows")
        if not a_counts["recordings"]:
            print("  WARNING: Account A has no recordings, so there is little to protect. "
                  "Send one recording as A and run this again.")

        print("\nAccount B asks Supabase for Account A's data:")
        ok = True

        def check(label: str, status: int, got: list, leaked: bool):
            nonlocal ok
            ok = ok and not leaked
            print(f"  {'LEAKED ' if leaked else 'BLOCKED'}  {label}: HTTP {status}, {len(got)} rows")

        for table in TABLES:
            status, got = rows(c, url, b_head, table, {"select": "*", "user_id": f"eq.{a_id}"})
            check(f"{table} where user is A", status, got, bool(got))
        if a_recording:
            status, got = rows(c, url, b_head, "recordings", {"select": "*", "id": f"eq.{a_recording}"})
            check("one of A's recordings, by its id", status, got, bool(got))
        for table in TABLES:
            status, got = rows(c, url, b_head, table, {"select": "*"})
            others = [r for r in got if r.get("user_id") != b_id]
            check(f"every row of {table} (B should get only its own)", status, others, bool(others))
        status, got = rows(c, url, b_head, "signup_codes", {"select": "*"})
        check("the sign-up codes table", status, got, bool(got))

        print("\nA visitor who is not signed in (public key only):")
        for table in TABLES + ("signup_codes",):
            status, got = rows(c, url, {"apikey": key}, table, {"select": "*"})
            check(table, status, got, bool(got))

    if ok and not a_counts["recordings"]:
        print(f"\nNOT PROVEN: nothing leaked on {name}, but Account A has no recordings to protect. "
              "Send one recording as A and run this again.")
    elif ok:
        print(f"\nPASS: on {name}, Account B and signed-out visitors cannot read Account A's data.")
    else:
        print(f"\nFAIL: on {name}, something marked LEAKED was readable. Tell pi.")


if __name__ == "__main__":
    main()
