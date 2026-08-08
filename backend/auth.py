"""
Optional API key auth.
------------------------
If API_KEY is unset (the default), `require_api_key` is a no-op and every
endpoint stays open — this is what keeps local dev/demo usage unchanged.
Set API_KEY in the environment to require `Authorization: Bearer <key>`
on the routes that use this dependency (state-changing endpoints only;
GETs are left open by design so read-only views/dashboards keep working
without a key).
"""
import os
from fastapi import Header, HTTPException

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def require_api_key(authorization: str | None = Header(default=None)):
    expected = os.environ.get("API_KEY", "").strip()
    if not expected:
        return  # auth disabled — no key configured
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or malformed Authorization header. Expected: Bearer <API_KEY>")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(401, "Invalid API key.")
