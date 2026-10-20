# Architecture

Indian Pharmacy Shop — Standalone is a single-deployable pharmacy billing and
inventory application. A React single-page UI talks to a Flask JSON API backed
by SQLAlchemy and SQLite. The same Flask process also serves the production
frontend build, so a deployment is one container or one Python process.

## System context

```text
                    +-----------------------------+
                    |        Web browser          |
                    |  React 18 + Vite SPA        |
                    |  token in localStorage      |
                    +--------------+--------------+
                                   |
                          HTTPS / JSON (Bearer)
                                   |
                    +--------------v--------------+
                    |        Flask + waitress     |
                    |  REST API  + static dist/   |
                    |  CORS, auth, billing logic  |
                    +--------------+--------------+
                                   |
                         SQLAlchemy ORM sessions
                                   |
                    +--------------v--------------+
                    |       SQLite database       |
                    |  pharmacy.db / /data volume |
                    +-----------------------------+
```

The frontend is optional at runtime: when `frontend/dist` exists, Flask serves
`index.html`, hashed JS/CSS assets, and uploaded logos. Without a build, the
API still runs and `/` returns a hint to build the UI.

## Technology stack

| Layer | Technology | Notes |
|---|---|---|
| UI | React 18, Vite 5 | Single-page app; no router or global state library |
| Build | Node.js 26, npm 11 | Vite production build |
| Styling | Plain CSS | `frontend/src/index.css` |
| API | Flask 3, Flask-CORS | JSON over `/api/*` |
| ORM | SQLAlchemy 2 | Typed declarative models |
| Database | SQLite | File or Docker volume; PostgreSQL URL supported if driver installed |
| Production server | waitress | Cross-platform WSGI server |
| Packaging | Docker multi-stage | Node build stage + Python runtime stage |
| CI/CD | GitHub Actions | Lint/test/build, GHCR image, GitHub Releases |

## Repository layout

```text
.
├── backend/
│   ├── app.py            # Flask app, auth, validation, all API routes
│   ├── models.py         # SQLAlchemy ORM models
│   ├── migrations.py     # Versioned, idempotent schema + seed migrations
│   ├── serve.py          # waitress entrypoint used by Docker/production
│   ├── requirements.txt
│   └── uploads/          # Store logos and optional catalogue imports
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js    # Dev proxy: /api -> Flask on :5000
│   ├── src/
│   │   ├── App.jsx       # Screens, forms, billing workflow, printing
│   │   ├── api.js        # Typed-ish API client + INR formatter
│   │   ├── index.css
│   │   └── main.jsx
│   └── dist/             # Generated production build (not hand-edited)
├── tests/                # Backend API and billing regression tests
├── USER_MANUAL.md        # Day-to-day user guide
├── INSTALLATION.md       # Installation and operations manual
├── README.md             # Project overview and quick start
├── launcher.py           # Desktop entrypoint for the packaged executable
├── pharmacy.spec         # PyInstaller one-file build specification
├── build_windows.bat     # Local Windows EXE build
├── docs/screenshots/     # README images
├── .github/workflows/
│   ├── ci.yml            # Pull-request and main-branch checks
│   ├── publish.yml       # GHCR image + tagged release artifacts
│   └── build-windows-exe.yml  # PyInstaller EXE + release asset
├── Dockerfile            # Multi-stage production image
├── docker-compose.yml    # Local/production compose with persistent volumes
├── ruff.toml             # Backend lint configuration
├── start.bat             # Windows one-click launcher
└── run.sh                # Linux/macOS launcher
```

## Backend design

### Application lifecycle

1. `app.py` reads configuration from environment variables and creates the
   SQLAlchemy engine.
2. `serve.py` calls `migrations.migrate()`, then starts waitress on
   `HOST:PORT` (default `0.0.0.0:5000`).
3. Each request opens a request-scoped session through `g.db`; the session is
   closed in `teardown_appcontext`.
4. `app.py` also mounts the compiled frontend at `/` and `/uploads/*` for
   store logos.

### Authentication and authorization

- `POST /api/login` checks a Werkzeug password hash and issues an opaque token.
- Tokens are stored in an in-process dictionary with a 12-hour default expiry
  (`SESSION_HOURS`). Restarting the server invalidates all sessions.
- The browser keeps the token in `localStorage` and sends
  `Authorization: Bearer <token>`.
- `require_auth` protects reads/writes; `require_admin` gates master-data,
  user-management, and destructive operations.
- The first-run admin is seeded from `ADMIN_USER` / `ADMIN_PASS`
  (default `admin` / `admin`). Change it immediately in production.

### Validation and business rules

- GST percentages must match an active row in `gst_rates`.
- Medicine units must match an active row in `unit_types`.
- Bill payment modes must match an active row in `payment_modes`.
- Stock quantity is decremented inside the bill transaction; insufficient
  stock is rejected.
- Returns mark the bill `returned` and restore stock.
- Every stock change is written to `stock_movements` for audit.
- Customers are auto-upserted from bill name/phone.
- Medicine and bill list endpoints support server-side pagination and filters.

### Module map in `app.py`

| Area | Representative routes |
|---|---|
| Health | `GET /api/health` |
| Sessions | `POST /api/login`, `POST /api/logout`, `GET /api/me` |
| Users | `GET/POST/DELETE /api/users`, `POST /api/change-password` |
| Masters | `/api/gst-rates`, `/api/unit-types`, `/api/payment-modes` |
| Store profile | `GET/PUT /api/settings`, `POST/DELETE /api/settings/logo` |
| Inventory | `/api/medicines`, `/api/medicines/:id/adjust` |
| Billing | `POST /api/bills`, `GET /api/bills`, return endpoint |
| Reporting | `GET /api/dashboard`, `GET /api/reports/sales` |
| Stock ledger | `GET /api/stock-movements`, `POST /api/purchases` |
| Directory | `/api/customers`, `/api/suppliers` |
| Static UI | `/`, `/uploads/<path>`, SPA fallback |

## Data model

```text
users                 gst_rates        unit_types       payment_modes
  id, username,         id, rate,        id, name,        id, name,
  password_hash,        is_active,       is_active,       is_active,
  is_admin,             created_at       created_at       created_at
  created_at

medicines             bills                              bill_items
  id                    id                                 id
  name                  customer_name, customer_phone      bill_id  -> bills.id
  composition           subtotal, gst_total                medicine_id
  unit                  discount_percent/amount            medicine_name
  batch_no              grand_total                        medicine_description
  expiry_date           payment_mode, status               medicine_usage
  quantity              doctor_name, prescription_no       qty, unit_price
  price, mrp            created_at                         gst_percent, line_total
  gst_percent
  description, usage    stock_movements                    customers
  supplier, rack          id, medicine_id, medicine_name     id, name, phone
  schedule                change, reason, ref               total_bills, total_spent
  rx_required             created_at, created_by            last_visit
  min_stock
                        store_settings (singleton id=1)
                          name, tagline, address, phone,
                          gstin, logo_path, low_stock_limit

                        schema_migrations
                          version, applied_at
```

Money is stored as floating point (`Float`). This is adequate for the current
single-store scale, but a future multi-currency or accounting-grade version
should move to integer paise or `Numeric`.

## Migrations

`migrate()` is called on every production start (and when running `app.py`
directly). It:

1. Creates any missing tables from SQLAlchemy metadata.
2. Reads applied versions from `schema_migrations`.
3. Runs each pending migration in order.
4. Records each successful version.

Migrations are idempotent and designed to upgrade legacy database files,
including adding columns to historical tables. To change the schema, append a
new `(version, name, function)` entry rather than editing an old migration.

The seed migrations create the admin user, GST slabs, units, payment modes,
store profile, and a starter medicine catalogue.

## Frontend design

- `App.jsx` is a single-page component tree with tab-style navigation
  (billing, inventory, purchases, reports, masters, settings).
- `api.js` centralises fetch calls, bearer-token injection, 401 handling, and
  the INR formatter.
- Vite proxies `/api` to Flask during development; production serves the
  hashed assets from `frontend/dist`.
- The billing screen keeps a local cart, validates stock, posts a bill, and
  renders a printable GST invoice.
- Builds are content-hashed; rebuilding is the supported way to change UI
  assets. Never edit `dist/` by hand.

## Deployment architecture

### Local / small store

```text
browser -> waitress (python serve.py) -> backend/pharmacy.db
```

`start.bat` installs dependencies, builds the UI on first run, and launches the
server on Windows. `run.sh` provides the equivalent Linux/macOS path.

### Docker / server

```text
browser -> published port :5000 -> container waitress -> /data/pharmacy.db
                                                        -> /app/backend/uploads
```

`docker-compose.yml` persists the database and uploads in named volumes and
defines a health check against `/api/health`. The container runs as a
non-root user (`uid 10001`).

### Windows executable

```text
double-click EXE -> launcher.py -> waitress on 127.0.0.1:5000
                                  -> bundled frontend/dist (PyInstaller _MEIPASS)
                                  -> %LOCALAPPDATA%\IndianPharmacyShop\pharmacy.db
```

`pharmacy.spec` builds a one-file executable that embeds Python, the backend,
and the frontend build. At runtime `backend/app.py` switches to a writable data
directory (`PHARMACY_DATA_DIR` or `%LOCALAPPDATA%\IndianPharmacyShop`) and reads
the UI from the PyInstaller extraction directory. The launcher picks a free port,
opens the default browser, and stops when the console window closes. The EXE is
not code-signed.

### CI/CD pipeline

- `ci.yml` runs on pull requests and pushes to `main`:
  - installs backend requirements, runs Ruff and `compileall`, runs pytest
    when a `tests/` directory exists;
  - installs frontend dependencies with `npm ci`, builds the UI, uploads the
    dist artifact;
  - builds the Docker image and waits for its health endpoint.
- `publish.yml` runs on pushes to `main`, version tags, and manual dispatch:
  - builds multi-architecture images (`linux/amd64`, `linux/arm64`);
  - pushes tags to GitHub Container Registry (`ghcr.io/<owner>/<repo>`);
  - on `v*` tags, builds the frontend and attaches a zip bundle to a GitHub
    Release.
- `build-windows-exe.yml` runs manually and on `v*` tags:
  - builds the frontend on a Windows runner;
  - packages the backend and UI with PyInstaller;
  - uploads `IndianPharmacyShop-windows.zip` and attaches it to tagged
    releases.

The Docker Hub image
(`vipulverulkar/indian-pharmacy-shop-standalone`) is published manually; the
automatic pipeline publishes to GHCR. Both images are built from the same
`Dockerfile`.

## Operational considerations

- **Backups:** copy `backend/pharmacy.db` (or the `pharmacy-data` volume) plus
  `backend/uploads`. SQLite backups should be taken while the app is stopped,
  or use SQLite's online backup API.
- **Scaling:** token sessions are in memory and SQLite is a single file, so the
  app is designed for one process per store. Horizontal scaling requires a
  shared database and shared session store.
- **Reverse proxy:** put nginx/Caddy in front for TLS, request limits, and
  compression. The app itself does not terminate TLS.
- **Security:** change the default admin password, keep `DATABASE_URL` and
  admin credentials in secrets, restrict CORS in a multi-origin deployment,
  and upload only trusted logo files.
- **Observability:** the health endpoint is the liveness/readiness probe;
  container logs contain waitress access and error output.
- **Media:** logos are limited to 2 MB by `MAX_CONTENT_LENGTH` and served from
  `/uploads/<filename>`.
