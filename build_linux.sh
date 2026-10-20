#!/bin/bash
# Build standalone Linux executable using PyInstaller

set -e

echo "=== Building Indian Pharmacy Shop Linux executable ==="

# Upgrade pip and install backend dependencies + PyInstaller
python3 -m pip install --upgrade pip
python3 -m pip install -r backend/requirements.txt pyinstaller

# Build frontend
cd frontend
npm ci
npm run build
cd ..

# Build executable
pyinstaller --noconfirm --clean pharmacy.spec

echo ""
echo "=== Build complete ==="
echo "Executable: dist/IndianPharmacyShop"
echo ""
echo "To run:"
echo "  ./dist/IndianPharmacyShop"