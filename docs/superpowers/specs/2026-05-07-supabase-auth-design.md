# Supabase Magic Link Auth — Design Spec
**Date:** 2026-05-07
**Status:** Approved

## Goal

Add admin authentication to the Observatory dashboard using Supabase magic link (passwordless email). The resume upload endpoint stays public but enforces one profile per email address (upsert semantics).

## Scope

**In scope:**
- Login overlay covering the dashboard until a valid Supabase session exists
- Magic link flow handled entirely by `@supabase/supabase-js` CDN client
- JWT verification on Flask via `PyJWT` + `SUPABASE_JWT_SECRET`
- `@require_auth` decorator applied to `/api/run-pipeline`, `/api/stats`, `/api/opportunities`, `/api/clusters`, `/api/recommendations`, `/api/users`, `/api/notifications`
- `/api/users/upload-resume` remains unauthenticated
- Upsert logic for resume upload: update existing user by email instead of returning 409

**Out of scope:**
- Role-based access control
- User-facing accounts (Supabase Auth is admin-only)
- Sign-up UI (admins are added directly in the Supabase dashboard)

## Architecture

```
Browser (Vercel)                     Flask (Render)
──────────────────                   ──────────────
Login overlay
  └─ supabase.auth.signInWithOtp()
       │ magic link email
       ▼
  supabase.auth.onAuthStateChange()
  session stored in localStorage
       │
  apiFetch() injects
  Authorization: Bearer <JWT>  ──►  @require_auth decorator
                                      PyJWT.decode(token,
                                        SUPABASE_JWT_SECRET,
                                        algorithms=["HS256"])
                                      401 if invalid/missing
                                      proceed if valid
```

## Frontend Changes (`dashboard/`)

### `templates/index.html`
- Add `@supabase/supabase-js` CDN script tag (before `dashboard.js`)
- Add login overlay `<div id="auth-overlay">` with email input and "Send Magic Link" button, hidden once authenticated
- Add logout button in sidebar

### `static/js/dashboard.js`
- Initialise Supabase client with `SUPABASE_URL` and `SUPABASE_ANON_KEY` (injected as JS constants, safe to expose)
- On `DOMContentLoaded`: call `supabase.auth.getSession()` — if no session, show overlay, skip `init()`
- `supabase.auth.onAuthStateChange`: when session arrives (after magic link click), hide overlay, call `init()`
- Inject `Authorization: Bearer <access_token>` header into `apiFetch()` and the `runPipeline` fetch
- Logout button calls `supabase.auth.signOut()` then reloads

### `vercel.json`
- No changes needed — Supabase JS handles the `#access_token` hash fragment automatically on the redirect back to the Vercel URL

## Backend Changes (`api/`)

### `config.py`
```python
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
```

### `api/app.py`
- Add `require_auth` decorator:
```python
import jwt  # PyJWT

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not token:
            return jsonify({"error": "Unauthorized"}), 401
        try:
            jwt.decode(token, config.SUPABASE_JWT_SECRET, algorithms=["HS256"],
                       options={"verify_aud": False})
        except jwt.PyJWTError:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
```
- Apply `@require_auth` to: `run_pipeline`, `stats`, and all blueprint routes except `upload_resume`

### `api/routes/users.py` — upsert on resume upload
- Before inserting a new user, query by email
- If found: `UPDATE users SET name=?, resume_text=? WHERE email=?`, delete old recommendations, rerun matching
- If not found: insert new user (current behavior)
- Return `200 OK` with recommendations in both cases (no more 409)

## Environment Variables

| Variable | Where | Value source |
|---|---|---|
| `SUPABASE_JWT_SECRET` | Render + local `.env` | Supabase dashboard → Project Settings → API → JWT Secret |
| `SUPABASE_URL` | Vercel env + hardcoded JS constant | Supabase dashboard → Project Settings → API |
| `SUPABASE_ANON_KEY` | Vercel env + hardcoded JS constant | Supabase dashboard → Project Settings → API |

`SUPABASE_URL` and `SUPABASE_ANON_KEY` are safe to expose in client JS (they're the public anon key, not the service role key).

## Dependencies

- **Frontend:** `@supabase/supabase-js` via CDN (no npm build step needed)
- **Backend:** `PyJWT` — add to `requirements.txt`

## Error Handling

- Expired/invalid JWT → `401 Unauthorized` from Flask; `apiFetch` propagates the error, existing error states in the UI display it
- Magic link expired (10 min default in Supabase) → Supabase JS shows an error; user can re-enter email
- No session on load → overlay shown, `init()` not called, no API requests made

## Testing

Run `python main.py --serve` locally with `SUPABASE_JWT_SECRET` set. Verify:
1. Dashboard shows login overlay with no session
2. After magic link → overlay hides, dashboard loads
3. Removing the `Authorization` header from a request returns 401
4. Resume upload works without any auth header
5. Uploading a second resume with the same email updates the profile instead of erroring
