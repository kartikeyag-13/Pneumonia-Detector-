# Pneumonia Detection API

FastAPI backend for a pneumonia-detection service.

- **Auth:** username/email + password (bcrypt hashes), short-lived JWT (120 min)
- **Images:** JPEG/PNG uploads (max 10 MB) verified with Pillow, stored in a **private** Supabase Storage bucket
- **Predictions:** `POST /predict/{image_id}` pipeline (ML model integration pending)
- **Database:** PostgreSQL via SQLAlchemy + Alembic

> **Note:** ML inference is **not** implemented yet. `POST /predict/{image_id}`
> returns `501 Not Implemented` until the model is integrated.

---

## Project layout

```
app/
  config.py          # settings loaded from env vars / .env
  database.py        # SQLAlchemy engine + session
  dependencies.py    # get_db, get_current_user (JWT)
  main.py            # FastAPI app + routers
  models/            # User, Image, Prediction
  routers/           # auth, images, predictions
  schemas/           # Pydantic response/request models
  services/          # storage.py (Supabase), inference.py (TODO)
  utils/security.py  # bcrypt + JWT helpers
alembic/             # DB migrations
```

---

## Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then fill in the values
alembic upgrade head      # create/apply DB schema
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs to try the API.

---

## Deploying to Render

The project runs as a **Web Service** (Python environment, no Docker).

### 1. Create the Render Web Service

1. Push this repository to GitHub/GitLab.
2. In the [Render dashboard](https://dashboard.render.com), click **New → Web Service**.
3. Connect the repository.
4. Name the service (e.g. `pneumonia-api`), choose **Python** as the runtime and a region.
5. Set the **Build Command** and **Start Command** below.
6. Add the environment variables from the table below.
7. Click **Create Web Service**. Render builds and deploys automatically.

### 2. Build command

```
pip install -r requirements.txt
```

### 3. Start command

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

(`$PORT` is injected by Render.)

### 4. Environment variables

Set all of these in the Render dashboard under **Environment**.

| Variable | Example / Notes |
| --- | --- |
| `DATABASE_USERNAME` | Supabase Postgres user |
| `DATABASE_PASSWORD` | Supabase Postgres password |
| `DATABASE_HOST` | Supabase Postgres host |
| `DATABASE_PORT` | `5432` |
| `DATABASE_NAME` | Supabase Postgres database name |
| `JWT_SECRET_KEY` | Long random string — generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service-role key (server-side only — never share with clients) |
| `SUPABASE_BUCKET` | `pneumonia-images` |

Notes:

- If the Supabase password contains URL-special characters (`@`, `/`, `:`, `%`, `#`), URL-encode them (e.g. `%40` for `@`), otherwise the app cannot connect.
- `SUPABASE_BUCKET` must exist in your Supabase project and be **private**. Only the service-role key accesses it.

### 5. Run Alembic migrations against the Supabase production database

The migrations build the connection from the same `DATABASE_*` variables as the app, so they always target the correct database. Pick one option:

**Option A — Render Shell (recommended):**

1. In the Render dashboard open your service → **Shell**.
2. Run `alembic upgrade head`.

**Option B — Pre-deploy command (automatic):**

1. In the dashboard → **Settings → Deploy → Pre-Deploy Command**.
2. Set it to `alembic upgrade head`.
3. Migrations run automatically before each deploy.

**Option C — Locally against production:**

```bash
export DATABASE_USERNAME=... DATABASE_PASSWORD=... DATABASE_HOST=... DATABASE_NAME=...
alembic upgrade head
```

(Or put the production values into a temporary `.env` — `.env` is gitignored.)

### 6. Verify `/docs`

After deploy, open:

```
https://<service-name>.onrender.com/docs
```

You should see the interactive Swagger UI listing `/auth/*`, `/images/upload`, `/predict/{image_id}`, and `/predictions*`. The raw OpenAPI spec is at `/openapi.json`. The root route `GET /` returns a JSON health message.

### 7. Test the full flow

Use `/docs`, or any HTTP client.

**1. Register**

```bash
curl -X POST https://<service-name>.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@example.com","password":"supersecret"}'
```

**2. Login** (capture `access_token`)

```bash
curl -X POST https://<service-name>.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"supersecret"}'
```

**3. Authorize**

In `/docs`, click **Authorize** (top right) and paste the token. The `HTTPBearer` scheme adds the `Bearer ` prefix automatically. For curl:

```bash
AUTH="Authorization: Bearer <access_token>"
```

**4. Upload an image** (JPEG/PNG, max 10 MB)

```bash
curl -X POST https://<service-name>.onrender.com/images/upload \
  -H "$AUTH" -F "file=@chest_xray.jpg"
```

**5. Predict** — take the `id` from the upload response

```bash
curl -X POST https://<service-name>.onrender.com/predict/<image_id> \
  -H "$AUTH"
```

> Currently returns `501` because ML inference is not integrated yet.

**6. History**

```bash
curl https://<service-name>.onrender.com/predictions -H "$AUTH"
curl https://<service-name>.onrender.com/predictions/<prediction_id> -H "$AUTH"
```

---

## Security notes

- Passwords are stored only as bcrypt hashes.
- Tokens expire after 120 minutes; protected routes require `Authorization: Bearer <token>`.
- Users can only access their own images and predictions.
- The Supabase bucket stays private; the service-role key is used server-side only and is never returned by the API.
- Replace the placeholder `JWT_SECRET_KEY` before any real deployment.
- `.env` and `.env.prod`/`.env.production` are gitignored; `.env.example` (no secrets) is committed.
