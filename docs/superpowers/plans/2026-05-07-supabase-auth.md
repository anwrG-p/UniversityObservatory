# Supabase Magic Link Auth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add magic-link admin auth to the Observatory dashboard using Supabase JS on the frontend and PyJWT verification on Flask, while keeping `/api/users/upload-resume` public and adding upsert-by-email semantics.

**Architecture:** Supabase JS client handles the magic-link flow in the browser and stores the session in localStorage. Every `apiFetch` call injects `Authorization: Bearer <jwt>` into the request. Flask verifies the JWT with PyJWT using `SUPABASE_JWT_SECRET` via a `require_auth` decorator defined in a new `api/auth.py` module and applied to all routes except `upload_resume`.

**Tech Stack:** Supabase JS v2 (CDN), PyJWT, Flask decorators

---

## File Map

| File | Action | What changes |
|---|---|---|
| `requirements.txt` | Modify | Add `PyJWT>=2.8.0` |
| `config.py` | Modify | Add `SUPABASE_JWT_SECRET` |
| `database/db_manager.py` | Modify | Add `get_user_by_email`, `update_user` |
| `api/auth.py` | **Create** | `require_auth` decorator |
| `api/app.py` | Modify | Import and apply `@require_auth` to `run_pipeline` and `stats` |
| `api/routes/opportunities.py` | Modify | Apply `@require_auth` to all 5 route functions |
| `api/routes/recommendations.py` | Modify | Apply `@require_auth` to `get_recommendations` |
| `api/routes/notifications.py` | Modify | Apply `@require_auth` to both route functions |
| `api/routes/users.py` | Modify | Apply `@require_auth` to `list_users`, `get_user`, `create_user`; upsert logic in `upload_resume` |
| `dashboard/templates/index.html` | Modify | Add Supabase CDN, constants, login overlay, logout button |
| `dashboard/static/js/dashboard.js` | Modify | Auth init, session check, inject header, logout |

---

## Task 1: Add PyJWT dependency and Supabase JWT secret config

**Files:**
- Modify: `requirements.txt`
- Modify: `config.py`

- [ ] **Step 1: Add PyJWT to requirements.txt**

Open `requirements.txt` and add one line after `pypdf==4.0.0`:
```
PyJWT==2.8.0
```

- [ ] **Step 2: Add SUPABASE_JWT_SECRET to config.py**

In `config.py`, add after the `SECRET_KEY` line (line 29):
```python
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
```

- [ ] **Step 3: Add the secret to your .env file**

Get the value from: Supabase dashboard → Project Settings → API → JWT Secret

Add to `.env`:
```
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-dashboard
```

- [ ] **Step 4: Verify config loads**

```bash
conda run -n HIDE python -c "import config; print('JWT secret set:', bool(config.SUPABASE_JWT_SECRET))"
```
Expected output: `JWT secret set: True`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt config.py
git commit -m "feat: add PyJWT dependency and SUPABASE_JWT_SECRET config"
```

---

## Task 2: Add `get_user_by_email` and `update_user` to DatabaseManager

**Files:**
- Modify: `database/db_manager.py` (after `insert_user`, around line 264)

- [ ] **Step 1: Add `get_user_by_email` method**

After the closing of `insert_user` in `database/db_manager.py`, add:
```python
def get_user_by_email(self, email: str) -> Optional[Dict]:
    rows = self.execute("SELECT * FROM users WHERE email = ?", (email,))
    return rows[0] if rows else None
```

- [ ] **Step 2: Add `update_user` method**

Directly after `get_user_by_email`, add:
```python
def update_user(self, user_id: int, data: Dict) -> None:
    self.execute(
        "UPDATE users SET name=?, profile=?, interests=?, skills=? WHERE id=?",
        (
            data.get("name", ""),
            data.get("profile", ""),
            data.get("interests", ""),
            data.get("skills", ""),
            user_id,
        ),
    )
```

- [ ] **Step 3: Verify both methods exist**

```bash
conda run -n HIDE python -c "from database.db_manager import DatabaseManager; db = DatabaseManager(); print(hasattr(db, 'get_user_by_email'), hasattr(db, 'update_user'))"
```
Expected: `True True`

- [ ] **Step 4: Commit**

```bash
git add database/db_manager.py
git commit -m "feat: add get_user_by_email and update_user to DatabaseManager"
```

---

## Task 3: Create `api/auth.py` with `require_auth` decorator

**Files:**
- Create: `api/auth.py`

- [ ] **Step 1: Create the file**

Create `api/auth.py` with this exact content:
```python
"""
api/auth.py
===========
JWT verification decorator for Flask routes.
Validates Supabase-issued JWTs using SUPABASE_JWT_SECRET.
"""

import jwt
from functools import wraps
from flask import request, jsonify
import config


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        token = auth_header[len("Bearer "):]
        try:
            jwt.decode(
                token,
                config.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
conda run -n HIDE python -c "from api.auth import require_auth; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add api/auth.py
git commit -m "feat: add require_auth JWT decorator"
```

---

## Task 4: Protect `run_pipeline` and `stats` in `api/app.py`

**Files:**
- Modify: `api/app.py`

- [ ] **Step 1: Import `require_auth` at the top of `api/app.py`**

After the existing imports in `api/app.py`, add:
```python
from api.auth import require_auth
```

- [ ] **Step 2: Apply decorator to `run_pipeline`**

Change line 64 from:
```python
    @app.route("/api/run-pipeline", methods=["POST"])
    def run_pipeline():
```
to:
```python
    @app.route("/api/run-pipeline", methods=["POST"])
    @require_auth
    def run_pipeline():
```

- [ ] **Step 3: Apply decorator to `stats`**

Change:
```python
    @app.route("/api/stats")
    def stats():
```
to:
```python
    @app.route("/api/stats")
    @require_auth
    def stats():
```

- [ ] **Step 4: Verify the app still starts**

```bash
conda run -n HIDE python -c "from api.app import create_app; app = create_app(); print('ok')"
```
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add api/app.py
git commit -m "feat: protect run_pipeline and stats with require_auth"
```

---

## Task 5: Protect blueprint routes

**Files:**
- Modify: `api/routes/opportunities.py`
- Modify: `api/routes/recommendations.py`
- Modify: `api/routes/notifications.py`
- Modify: `api/routes/users.py`

- [ ] **Step 1: Update `api/routes/opportunities.py`**

Add import after existing imports:
```python
from api.auth import require_auth
```

Add `@require_auth` decorator to all five route functions:
```python
@opportunities_bp.route("/opportunities", methods=["GET"])
@require_auth
def list_opportunities():
    ...

@opportunities_bp.route("/opportunities/<int:opp_id>", methods=["GET"])
@require_auth
def get_opportunity(opp_id: int):
    ...

@opportunities_bp.route("/clusters", methods=["GET"])
@require_auth
def list_clusters():
    ...

@opportunities_bp.route("/clusters/pca", methods=["GET"])
@require_auth
def pca_coords():
    ...

@opportunities_bp.route("/clusters/<int:cluster_id>/opportunities", methods=["GET"])
@require_auth
def cluster_opportunities(cluster_id: int):
    ...
```

- [ ] **Step 2: Update `api/routes/recommendations.py`**

Add import:
```python
from api.auth import require_auth
```

Add decorator:
```python
@recommendations_bp.route("/recommendations/<int:user_id>", methods=["GET"])
@require_auth
def get_recommendations(user_id: int):
    ...
```

- [ ] **Step 3: Update `api/routes/notifications.py`**

Add import:
```python
from api.auth import require_auth
```

Add decorator to both functions:
```python
@notifications_bp.route("/notifications/<int:user_id>", methods=["GET"])
@require_auth
def get_notifications(user_id: int):
    ...

@notifications_bp.route("/notifications/<int:notif_id>/read", methods=["PATCH"])
@require_auth
def mark_read(notif_id: int):
    ...
```

- [ ] **Step 4: Update `api/routes/users.py` — protect all routes except `upload_resume`**

Add import:
```python
from api.auth import require_auth
```

Add decorator to `list_users`, `get_user`, and `create_user` — **NOT** `upload_resume`:
```python
@users_bp.route("/users", methods=["GET"])
@require_auth
def list_users():
    ...

@users_bp.route("/users/<int:user_id>", methods=["GET"])
@require_auth
def get_user(user_id: int):
    ...

@users_bp.route("/users", methods=["POST"])
@require_auth
def create_user():
    ...

@users_bp.route("/users/upload-resume", methods=["POST"])
def upload_resume():   # ← no @require_auth — intentionally public
    ...
```

- [ ] **Step 5: Verify all routes load**

```bash
conda run -n HIDE python -c "from api.app import create_app; app = create_app(); rules = [str(r) for r in app.url_map.iter_rules()]; print('\n'.join(sorted(rules)))"
```
Expected: all routes listed, no import errors.

- [ ] **Step 6: Commit**

```bash
git add api/routes/opportunities.py api/routes/recommendations.py api/routes/notifications.py api/routes/users.py
git commit -m "feat: apply require_auth to all blueprint routes except upload_resume"
```

---

## Task 6: Upsert-by-email in `upload_resume`

**Files:**
- Modify: `api/routes/users.py`

- [ ] **Step 1: Replace the user-creation block in `upload_resume`**

Find the block in `upload_resume` that creates the user (lines 68–80):
```python
    # Create User
    user_data = {
        "name": name,
        "email": email,
        "profile": text[:2000],
        "interests": "",
        "skills": ""
    }
    
    try:
        user_id = _db().insert_user(user_data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 409
```

Replace it with:
```python
    # Upsert: update existing user or create new one
    user_data = {
        "name": name,
        "email": email,
        "profile": text[:2000],
        "interests": "",
        "skills": "",
    }

    existing = _db().get_user_by_email(email)
    if existing:
        user_id = existing["id"]
        _db().update_user(user_id, user_data)
        # Clear old recommendations so they are regenerated fresh
        _db().execute("DELETE FROM recommendations WHERE user_id = ?", (user_id,))
    else:
        try:
            user_id = _db().insert_user(user_data)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
```

- [ ] **Step 2: Verify the endpoint loads**

```bash
conda run -n HIDE python -c "from api.routes.users import users_bp; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Manual smoke test — duplicate email**

Start the server: `conda run -n HIDE python main.py --serve`

Upload a PDF once via the Resume Match UI. Note the returned recommendations.
Upload the same email again with a different PDF. Expect:
- `200 OK` (not `409`)
- Fresh recommendations returned

- [ ] **Step 4: Commit**

```bash
git add api/routes/users.py
git commit -m "feat: upsert resume upload by email — update existing user instead of 409"
```

---

## Task 7: Frontend — login overlay and Supabase CDN

**Files:**
- Modify: `dashboard/templates/index.html`

- [ ] **Step 1: Add Supabase CDN script and public constants**

In `dashboard/templates/index.html`, after the existing `<link rel="preload" ...>` lines and before `</head>`, add:
```html
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
  <script>
    // Public Supabase credentials — safe to expose in client JS
    const SUPABASE_URL      = "https://wjtuwtkcqipzdulzcphb.supabase.co";
    const SUPABASE_ANON_KEY = "YOUR_ANON_KEY_FROM_SUPABASE_DASHBOARD";
  </script>
```

To get `SUPABASE_ANON_KEY`: Supabase dashboard → Project Settings → API → `anon` `public` key.
To get `SUPABASE_URL`: same page → Project URL.

- [ ] **Step 2: Add login overlay to `<body>`**

Add this as the very first child of `<body>`, before `<div class="bg-canvas">`:
```html
<!-- Auth overlay — shown until a valid Supabase session exists -->
<div id="auth-overlay" style="
  position:fixed;inset:0;z-index:9999;
  background:var(--bg-deep,#080e1c);
  display:flex;align-items:center;justify-content:center;
">
  <div style="
    background:var(--bg-surface,#0d1628);
    border:1px solid rgba(255,255,255,0.08);
    border-radius:12px;padding:2.5rem;width:340px;
    display:flex;flex-direction:column;gap:1rem;
    box-shadow:0 8px 32px rgba(0,0,0,0.4);
  ">
    <div style="text-align:center;margin-bottom:0.5rem">
      <div style="font-size:1.5rem;font-weight:700;color:#e2e8f0">Observatory</div>
      <div style="font-size:0.85rem;color:#94a3b8;margin-top:4px">Enter your email to receive a magic link</div>
    </div>
    <input id="auth-email" type="email" placeholder="you@example.com" style="
      background:var(--bg-deep,#080e1c);border:1px solid rgba(255,255,255,0.1);
      border-radius:6px;padding:0.65rem 0.9rem;color:#e2e8f0;
      font-size:0.9rem;width:100%;box-sizing:border-box;outline:none;
    "/>
    <button id="auth-btn" style="
      background:#4f8ef7;color:#fff;border:none;border-radius:6px;
      padding:0.7rem;font-size:0.9rem;font-weight:600;cursor:pointer;width:100%;
    ">Send Magic Link</button>
    <div id="auth-msg" style="font-size:0.8rem;color:#94a3b8;text-align:center;min-height:1.2em"></div>
  </div>
</div>
```

- [ ] **Step 3: Add logout button to sidebar**

In the sidebar nav section, after the last `<a class="nav-link">` and before `</nav>`, add:
```html
      <div class="nav-section" style="margin-top:auto">Session</div>
      <button id="btn-logout" class="nav-link" style="background:none;border:none;cursor:pointer;text-align:left;width:100%;color:inherit;">
        <span class="nav-icon">⏏</span><span>Sign out</span>
      </button>
```

- [ ] **Step 4: Verify HTML is valid**

Open `http://localhost:5000` in a browser after starting the server. The overlay should cover the page.

- [ ] **Step 5: Commit**

```bash
git add dashboard/templates/index.html
git commit -m "feat: add Supabase CDN, login overlay, and logout button to dashboard"
```

---

## Task 8: Frontend — auth logic in `dashboard.js`

**Files:**
- Modify: `dashboard/static/js/dashboard.js`

- [ ] **Step 1: Add Supabase client init and session state at the top of the file**

After the `// ── State ─────` block (after line 39, `let chartClusters = null;`), add:
```js
// ── Auth ─────────────────────────────────────────────────
const _supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
let _session = null;
```

- [ ] **Step 2: Inject Authorization header in `apiFetch`**

Replace the existing `apiFetch` function (lines 50–54):
```js
async function apiFetch(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${path}`);
  return res.json();
}
```
with:
```js
async function apiFetch(path) {
  const headers = {};
  if (_session?.access_token) {
    headers["Authorization"] = `Bearer ${_session.access_token}`;
  }
  const res = await fetch(API + path, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${path}`);
  return res.json();
}
```

- [ ] **Step 3: Inject auth header into `runPipeline` fetch**

In `runPipeline`, replace:
```js
    const result = await fetch(`${API}/api/run-pipeline`, { method: "POST" });
```
with:
```js
    const result = await fetch(`${API}/api/run-pipeline`, {
      method: "POST",
      headers: _session?.access_token
        ? { "Authorization": `Bearer ${_session.access_token}` }
        : {},
    });
```

- [ ] **Step 4: Replace `init` with auth-aware bootstrap**

Replace the entire `init` function and `document.addEventListener("DOMContentLoaded", init)` at the bottom of the file with:
```js
// ── Auth bootstrap ─────────────────────────────────────────
async function authInit() {
  const overlay  = document.getElementById("auth-overlay");
  const authBtn  = document.getElementById("auth-btn");
  const authMsg  = document.getElementById("auth-msg");
  const authEmail = document.getElementById("auth-email");

  // Magic link send
  authBtn.addEventListener("click", async () => {
    const email = authEmail.value.trim();
    if (!email) { authMsg.textContent = "Please enter your email."; return; }
    authBtn.disabled = true;
    authMsg.textContent = "Sending…";
    const { error } = await _supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    authBtn.disabled = false;
    authMsg.textContent = error ? `Error: ${error.message}` : "✅ Check your email for the magic link.";
  });

  // Logout
  document.getElementById("btn-logout").addEventListener("click", async () => {
    await _supabase.auth.signOut();
    window.location.reload();
  });

  // React to auth state changes (including magic link redirect)
  _supabase.auth.onAuthStateChange(async (event, session) => {
    _session = session;
    if (session) {
      overlay.style.display = "none";
      await init();
    } else {
      overlay.style.display = "flex";
    }
  });

  // Check for existing session on load
  const { data } = await _supabase.auth.getSession();
  _session = data.session;
  if (_session) {
    overlay.style.display = "none";
    await init();
  }
}

async function init() {
  $("btn-run-pipeline").addEventListener("click", runPipeline);
  $("resume-form").addEventListener("submit", handleResumeUpload);
  $("btn-filter").addEventListener("click", () => {
    loadOpportunities($("filter-type").value, $("filter-location").value);
  });
  $("btn-reset-filter").addEventListener("click", () => {
    $("filter-type").value = "";
    $("filter-location").value = "";
    loadOpportunities();
  });
  $("btn-prev").addEventListener("click", () => { currentPage--; renderTable(); });
  $("btn-next").addEventListener("click", () => { currentPage++; renderTable(); });

  await Promise.all([loadStats(), loadOpportunities(), loadUsers()]);
  await loadClusters();
}

document.addEventListener("DOMContentLoaded", authInit);
```

- [ ] **Step 5: End-to-end manual test**

1. Start server: `conda run -n HIDE python main.py --serve`
2. Open `http://localhost:5000` — overlay should appear
3. Enter your admin email → click "Send Magic Link"
4. Click the link in your email → page should reload, overlay disappear, dashboard load
5. Reload the page — should stay logged in (session in localStorage)
6. Click "Sign out" → overlay should reappear
7. Without logging in, use curl to verify protection:
   ```bash
   curl -s http://localhost:5000/api/stats
   # Expected: {"error":"Unauthorized"} with HTTP 401
   ```
8. Verify resume upload still works without auth:
   ```bash
   curl -s -X POST http://localhost:5000/api/users/upload-resume \
     -F "name=Test User" -F "email=test@test.com" -F "file=@some.pdf"
   # Expected: 200 with recommendations (or empty list if no opps in DB)
   ```

- [ ] **Step 6: Commit**

```bash
git add dashboard/static/js/dashboard.js
git commit -m "feat: add Supabase magic link auth flow to dashboard"
```

---

## Task 9: Set environment variables on Render

- [ ] **Step 1: Add `SUPABASE_JWT_SECRET` to Render**

Render dashboard → your service → Environment → Add variable:
- Key: `SUPABASE_JWT_SECRET`
- Value: (from Supabase dashboard → Project Settings → API → JWT Secret)

- [ ] **Step 2: Redeploy and smoke test production**

After deploy completes:
```bash
curl -s https://universityobservatory.onrender.com/api/stats
# Expected: {"error":"Unauthorized"}
```

Open `https://universityobservatory.onrender.com` in browser — overlay should appear.
Complete magic link login — dashboard should load with data.

- [ ] **Step 3: Final commit (if any config drift)**

```bash
git add .
git commit -m "chore: verify Supabase auth working in production"
```
