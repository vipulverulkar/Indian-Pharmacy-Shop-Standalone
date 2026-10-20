@echo off
setlocal
cd /d "%~dp0"

python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt pyinstaller
if errorlevel 1 goto :failed

pushd frontend
call npm ci
if errorlevel 1 goto :failed
call npm run build
if errorlevel 1 goto :failed
popd

pyinstaller --noconfirm --clean pharmacy.spec
if errorlevel 1 goto :failed

echo.
echo Built dist\IndianPharmacyShop.exe
pause
exit /b 0

:failed
echo.
echo Build failed. Check the messages above.
pause
exit /b 1
