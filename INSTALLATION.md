# Installation Manual

This manual covers local installation, production deployment, upgrades, backups,
and troubleshooting for Indian Pharmacy Shop — Standalone.

- Repository: <https://github.com/vipulverulkar/Indian-Pharmacy-Shop-Standalone>
- Stack: React 18 + Vite, Flask 3, SQLAlchemy 2, SQLite, waitress
- Default login after first start: `admin` / `admin` (change it immediately)

## 1. Requirements

### Minimum

| Component | Version | Needed for |
|---|---|---|
| Python | 3.10 or newer | Backend API and migrations |
| Node.js | 18 or newer | Building the React UI from source |
| npm | Bundled with Node | Frontend dependencies |
| Docker | 24 or newer (optional) | Container deployment |

You do not need Node.js to run a prebuilt copy if `frontend/dist` is already
present. The backend serves that build directly.

### Ports and disk

- Default HTTP port: `5000` (override with `PORT`).
- SQLite database: `backend/pharmacy.db` (about 100–200 MB for a busy store).
- Uploads: `backend/uploads` (store logos, optional import CSV).
- Docker volumes: `pharmacy-data`, `pharmacy-uploads`.

## 2. Quick start (Docker, recommended)

Docker is the simplest way to get a reproducible deployment.

```bash
git clone https://github.com/vipulverulkar/Indian-Pharmacy-Shop-Standalone.git
cd Indian-Pharmacy-Shop-Standalone
docker compose up -d --build
```

Open <http://localhost:5000> and log in with `admin` / `admin`.

If port 5000 is already in use:

```bash
HOST_PORT=5001 docker compose up -d --build
# open http://localhost:5001
```

Check status and logs:

```bash
docker compose ps
docker compose logs -f pharmacy
```

Stop the app:

```bash
docker compose down       # keeps data
docker compose down -v    # deletes database and uploads volumes
```

### Run the published image instead of building

The CI pipeline publishes images to GitHub Container Registry:

```bash
docker pull ghcr.io/vipulverulkar/indian-pharmacy-shop-standalone:latest

docker run -d --name pharmacy \
  -p 5000:5000 \
  -v pharmacy-data:/data \
  -v pharmacy-uploads:/app/backend/uploads \
  ghcr.io/vipulverulkar/indian-pharmacy-shop-standalone:latest
```

Private packages require a GHCR login:

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <github-user> --password-stdin
```

## 3. Install from source

### 3.1 Clone and install backend dependencies

```bash
git clone https://github.com/vipulverulkar/Indian-Pharmacy-Shop-Standalone.git
cd Indian-Pharmacy-Shop-Standalone

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 3.2 Build the frontend

```bash
cd frontend
npm ci
npm run build
cd ..
```

`npm ci` requires `package-lock.json`, which is committed. Use `npm install` only
when intentionally updating dependencies.

### 3.3 Start the application

Development server (auto-reload, not for production):

```bash
cd backend
python app.py
```

Production server (waitress):

```bash
cd backend
python serve.py
```

Both create `backend/pharmacy.db` and apply all migrations on first start.
Open <http://127.0.0.1:5000>.

To use a different port:

```bash
PORT=5001 python serve.py
```

### 3.4 Windows one-click launcher

On Windows, double-click `start.bat`. It creates a virtual environment, installs
dependencies, builds the UI when needed, and opens the browser. If port 5000 is
busy:

```bat
start.bat 5001
```

### 3.5 Frontend development with hot reload

Run the backend on port 5000 in one terminal, then:

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. Vite proxies `/api` to Flask. To point at another
backend port:

```bash
API_URL=http://127.0.0.1:5001 npm run dev
```

## 4. Configuration

Configuration is read from environment variables at process start.

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` (`127.0.0.1` in `app.py`) | Bind address for `serve.py` |
| `PORT` | `5000` | HTTP port |
| `ADMIN_USER` | `admin` | Seeded admin username (first run only) |
| `ADMIN_PASS` | `admin` | Seeded admin password (first run only) |
| `SESSION_HOURS` | `12` | Bearer-token lifetime in hours |
| `DATABASE_URL` | `sqlite:///backend/pharmacy.db` | SQLAlchemy database URL |
| `API_URL` | `http://127.0.0.1:5000` | Dev-only Vite proxy target |

The admin variables are used only while seeding. Changing them later does not
alter an existing user; use the Users tab or `POST /api/change-password`.

### PostgreSQL (optional)

SQLite is the supported standalone default. To use PostgreSQL, install a driver
(for example `psycopg2-binary`) in the environment and set:

```bash
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/pharmacy
```

The Dockerfile does not include a PostgreSQL driver. Extend the requirements and
image if you need this in a container.

### Docker environment overrides

The compose file passes `HOST` and `PORT` defaults. Add variables under the
`pharmacy` service:

```yaml
services:
  pharmacy:
    environment:
      ADMIN_USER: owner
      ADMIN_PASS: change-me
      SESSION_HOURS: "8"
```

Use Docker secrets or an `.env` file for real credentials; never commit them.

## 5. First-run checklist

1. Open the app and log in with `admin` / `admin`.
2. Open **Settings** and set the store name, address, phone, GSTIN, and logo.
3. Open **Users** and change the admin password.
4. Create staff users if needed (staff can bill and view inventory).
5. Review **Masters**: GST slabs, unit types, and payment modes.
6. Add or import medicines, set low-stock limits, and verify stock.
7. Create a test bill and print it to confirm the invoice layout.
8. Back up the database before entering real transactions.

## 6. Database, uploads, and backups

### Local install

- Database: `backend/pharmacy.db`
- Logos: `backend/uploads/`
- Optional import CSV: `backend/uploads/medicine_data.csv`

Back up while the server is stopped:

```bash
cp backend/pharmacy.db "pharmacy-$(date +%F).db"
tar -czf "pharmacy-uploads-$(date +%F).tar.gz" backend/uploads
```

Restore by stopping the server, replacing the database file, and restarting.
Migrations will upgrade an older database automatically.

### Docker

Named volumes hold the data:

```bash
docker run --rm \
  -v pharmacy-data:/data \
  -v "$PWD:/backup" \
  alpine cp /data/pharmacy.db "/backup/pharmacy-$(date +%F).db"
```

Uploads:

```bash
docker run --rm \
  -v pharmacy-uploads:/app/backend/uploads \
  -v "$PWD:/backup" \
  alpine tar -czf /backup/uploads.tar.gz -C /app/backend/uploads .
```

Restore:

```bash
docker compose down
docker run --rm -v pharmacy-data:/data -v "$PWD:/backup" alpine \
  cp /backup/pharmacy-YYYY-MM-DD.db /data/pharmacy.db
docker compose up -d
```

### Migrations

Migrations run automatically at every start. Never edit `schema_migrations` by
hand. To verify a database:

```bash
cd backend
python -c "from app import engine, migrate; print(migrate(engine))"
```

An empty list means the database is up to date.

## 7. Testing and CI/CD

### Local checks

```bash
# Backend
pip install ruff pytest
ruff check backend
python -m compileall -q backend
python -m pytest -q

# Frontend
cd frontend && npm ci && npm run build && cd ..

# Container
docker build -t pharmacy-app .
docker run -d --name pharmacy-test -p 5000:5000 pharmacy-app
curl http://127.0.0.1:5000/api/health
docker rm -f pharmacy-test
```

### GitHub Actions

- **CI** (`.github/workflows/ci.yml`) runs on pull requests and pushes to
  `main`: Ruff, `compileall`, optional pytest, `npm ci` + build, Docker build,
  and a container health check.
- **Publish** (`.github/workflows/publish.yml`) runs on `main`, version tags,
  and manual dispatch:
  - pushes multi-arch images to GHCR;
  - creates a GitHub Release with a frontend bundle for tags such as `v1.0.0`.

Create a release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Required repository permissions are already declared in the workflow files
(`packages: write` for GHCR, `contents: write` for releases). No extra secrets
are needed when using `GITHUB_TOKEN`.

## 8. Production deployment notes

- Terminate TLS with nginx, Caddy, or a cloud load balancer. The app does not
  handle HTTPS itself.
- Bind waitress to the private interface and publish only the reverse proxy.
- Run the container as the built-in non-root user; do not override `USER`.
- Set a strong `ADMIN_PASS` before the first start, or change it immediately
  after login.
- Keep the database and uploads on persistent storage and include them in
  scheduled backups.
- Monitor `GET /api/health`; it returns `{"status": "ok"}` when the API is up.
- Sessions are held in memory, so a restart logs everyone out. This is expected
  for the single-store design.
- For multiple app instances, move sessions to shared storage and use
  PostgreSQL instead of SQLite.

### Example nginx reverse proxy

```nginx
server {
    listen 80;
    server_name pharmacy.example.com;

    client_max_body_size 3m;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Add TLS with Certbot or your platform's certificate manager.

## 9. Upgrades

1. Back up the database and uploads.
2. Pull the new version:
   ```bash
   git pull
   ```
3. Rebuild the frontend and image:
   ```bash
   cd frontend && npm ci && npm run build && cd ..
   docker compose up -d --build
   ```
4. Check logs and `/api/health`.
5. Migrations run automatically; keep the previous database backup until the
   new version has been verified.

To pin a version, deploy a tagged image instead of `latest`:

```bash
docker pull ghcr.io/vipulverulkar/indian-pharmacy-shop-standalone:1.0.0
```

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Login required` immediately after restart | In-memory sessions were cleared | Log in again; expected behavior |
| `Address already in use` | Port 5000 is busy | Use `PORT=5001` or `HOST_PORT=5001` |
| Page shows "Build the frontend" | `frontend/dist` missing | Run `cd frontend && npm ci && npm run build` |
| `npm ci` fails | Lockfile or Node version mismatch | Use Node 18+ and keep `package-lock.json` |
| `No module named flask` | Dependencies not installed in the active environment | Activate the venv and reinstall `backend/requirements.txt` |
| GST/unit/payment validation errors | Value is not in the active masters | Add or activate it under Masters |
| Product images 404 | Uploads volume not mounted | Mount `/app/backend/uploads` or use compose |
| Database locked | Multiple writers or a network filesystem | Run one process; keep SQLite on local disk |
| Container unhealthy | Migrations or startup error | `docker logs pharmacy` and test `/api/health` |
| GHCR `denied` | Package is private or token lacks scope | `docker login ghcr.io` with a valid token |

### Reset a development database

This deletes all data. Only do it on a development machine:

```bash
rm backend/pharmacy.db
cd backend && python serve.py   # recreates and seeds
```

For Docker:

```bash
docker compose down -v
docker compose up -d --build
```

## 11. Uninstall

Local install:

```bash
deactivate
rm -rf .venv frontend/node_modules frontend/dist
rm -f backend/pharmacy.db
```

Docker:

```bash
docker compose down -v
docker image rm pharmacy-app:latest
```

Remove any backups you no longer need.
