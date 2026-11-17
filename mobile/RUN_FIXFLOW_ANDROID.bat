@echo off
setlocal
cd /d "%~dp0"
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
set "PATH=%JAVA_HOME%\bin;%PATH%"
set "FLUTTER_SUPPRESS_ANALYTICS=true"

echo Building and starting FixFlow on the running Android emulator...
set "FLUTTER_BAT=%USERPROFILE%\Documents\Codex\.tools\flutter-clean\flutter\bin\flutter.bat"
if not exist "%FLUTTER_BAT%" (
  where flutter >nul 2>nul
  if errorlevel 1 (
    echo Flutter was not found. Install Flutter or add it to PATH, then run this file again.
    pause
    exit /b 1
  )
  set "FLUTTER_BAT=flutter"
)
call "%FLUTTER_BAT%" run --dart-define=API_BASE_URL=http://10.0.2.2:8001/api/v1
set "RUN_EXIT_CODE=%ERRORLEVEL%"

if not "%RUN_EXIT_CODE%"=="0" (
  echo.
  echo FixFlow did not start. Please send a screenshot of this window.
)

pause
exit /b %RUN_EXIT_CODE%
