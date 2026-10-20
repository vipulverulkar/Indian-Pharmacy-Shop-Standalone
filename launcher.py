"""Desktop launcher for the packaged executable.

Starts the waitress server, opens the browser, and keeps running until the
console window is closed. The database and uploads live in a writable data
directory (see PHARMACY_DATA_DIR / %LOCALAPPDATA%\\IndianPharmacyShop).
"""

import os
import socket
import sys
import threading
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
if os.path.isdir(BACKEND_DIR) and BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import ADMIN_PASS, ADMIN_USER, BASE_DIR, DATABASE_URL, app, engine, migrate


def _free_port(start=5000, end=5100):
    requested = os.environ.get("PORT")
    if requested:
        return int(requested)
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port between {start} and {end}")


def _open_browser(url):
    time.sleep(1.5)
    webbrowser.open(url)


def main():
    applied = migrate(engine, ADMIN_USER, ADMIN_PASS)
    if applied:
        print(f"Applied migrations: {applied}")

    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    print("Indian Pharmacy Shop")
    print(f"Opening {url}")
    print(f"Data directory: {BASE_DIR}")
    print(f"Database: {DATABASE_URL}")
    print("Close this window to stop the server.")

    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    from waitress import serve

    serve(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
