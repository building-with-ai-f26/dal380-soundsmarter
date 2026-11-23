"""Reverse proxy for PostHog analytics.

Ad blockers (e.g. Brave Shields) block requests to posthog.com, so testers on
those browsers were invisible. Instead, the page sends analytics to this app's
own address (/ingest/...), and this code forwards each request to PostHog.
PostHog's recommended setup: https://posthog.com/docs/advanced/proxy

Nothing here touches our API keys; it only relays what the browser sends.
It relays only the PostHog addresses the page uses (ALLOWED), nothing else.
"""

import httpx
from fastapi import APIRouter, Request, Response

PREFIX = "/ingest"
API_HOST = "https://us.i.posthog.com"            # events, session replay, flags
ASSET_HOST = "https://us-assets.i.posthog.com"   # PostHog's own JavaScript files
MAX_BODY_BYTES = 5_000_000  # session-replay batches are small; refuse anything huge
# First part of each PostHog address the page calls: events (e, i, batch, capture, engage,
# track), session replay (s), feature flags and settings (flags, decide), and PostHog's own
# JavaScript (static, array). Anything else is refused, so this is not a general relay.
ALLOWED = {"e", "i", "batch", "capture", "engage", "track", "s", "flags", "decide", "static", "array"}

router = APIRouter()


def target_url(path: str, query: str = "") -> str:
    """Map /ingest/<path> to the matching PostHog address."""
    host = ASSET_HOST if path.startswith(("static/", "array/")) else API_HOST
    return f"{host}/{path}" + (f"?{query}" if query else "")


def allowed(path: str) -> bool:
    parts = path.split("/")
    if ".." in parts or "." in parts:  # "e/../api" would climb out of the allowed address
        return False
    return parts[0] in ALLOWED


@router.api_route(PREFIX + "/{path:path}", methods=["GET", "POST"])
async def ingest(path: str, request: Request):
    if not allowed(path):
        return Response(status_code=404)
    body = b""
    async for chunk in request.stream():  # stop reading as soon as it is too big
        body += chunk
        if len(body) > MAX_BODY_BYTES:
            return Response(status_code=413)
    headers = {k: v for k, v in request.headers.items()
               if k.lower() in ("content-type", "content-encoding", "user-agent", "accept")}
    # Pass on the visitor's IP so PostHog's location data isn't all "the server"
    client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")
    if client_ip:
        headers["x-forwarded-for"] = client_ip
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.request(request.method, target_url(path, request.url.query),
                                    headers=headers, content=body)
    # httpx already unzipped the reply, so don't claim it's still compressed
    keep = {k: v for k, v in resp.headers.items()
            if k.lower() in ("content-type", "cache-control")}
    keep["X-Content-Type-Options"] = "nosniff"  # browsers must not guess a different file type
    return Response(content=resp.content, status_code=resp.status_code, headers=keep)
