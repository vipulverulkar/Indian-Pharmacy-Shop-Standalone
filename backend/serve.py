"""
Indian Pharmacy Shop - Windows-friendly production server
Copyright (C) 2024 Vipul Verulkar

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import os

from app import ADMIN_PASS, ADMIN_USER, app, engine, migrate

if __name__ == "__main__":
    applied = migrate(engine, ADMIN_USER, ADMIN_PASS)
    if applied:
        print(f"Applied migrations: {applied}")
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    print(f"Serving at http://{host}:{port}/ (login: admin / admin)")
    from waitress import serve

    serve(app, host=host, port=port)
