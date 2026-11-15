# FixFlow Android technician app

The Flutter app connects to the existing FixFlow API. It supports technician sign-in, assigned requests, request details (including address and preferred visit time), work status actions, and shared notes. It does not use mock requests. Access tokens use Android secure storage.

## Prerequisites

- Flutter SDK and Android Studio with Android SDK installed.
- An Android Virtual Device (AVD) or a physical Android phone.
- The FixFlow API running and reachable from the device.

The Android project wrapper is already included in `android/`; do not run `flutter create` again.

## Start in the Android emulator

Start an AVD from Android Studio: **More Actions → Virtual Device Manager → ▶**. For the Android emulator, the host machine is available at `10.0.2.2`, so the default API address is `http://10.0.2.2:8001/api/v1`.

From this `mobile` directory, run:

```powershell
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8001/api/v1 --dart-define=DEFAULT_ORGANIZATION_ID=<organization-id>
```

Use the organization ID printed by `docker compose exec backend uv run --no-sync python -m app.seed`. The API must be running on port 8001.

If the emulator cannot start because hardware acceleration is unavailable, enable **Windows Hypervisor Platform** in Windows Features and restart Windows. An emulator also needs several gigabytes of free disk space. A physical Android phone can be used instead.

## Start on a physical Android phone

Connect the phone and computer to the same trusted Wi-Fi network. Configure the API to listen on the LAN (for example, set `HOST_BIND=0.0.0.0` in the ignored project `.env`) and allow port 8001 through Windows Firewall for the private network. Find the computer's LAN IPv4 address, then run:

```powershell
flutter run --dart-define=API_BASE_URL=http://<computer-lan-ip>:8001/api/v1 --dart-define=DEFAULT_ORGANIZATION_ID=<organization-id>
```

For a deployed service, use HTTPS instead of cleartext HTTP.

## Build APK

A debug APK can be built for local installation with:

```powershell
flutter build apk --debug --dart-define=API_BASE_URL=http://10.0.2.2:8001/api/v1 --dart-define=DEFAULT_ORGANIZATION_ID=<organization-id>
```

A release APK for deployment must use the public HTTPS API address and a configured signing key:

```powershell
flutter build apk --release --dart-define=API_BASE_URL=https://<your-api-host>/api/v1 --dart-define=DEFAULT_ORGANIZATION_ID=<organization-id>
```

APK output: `build/app/outputs/flutter-apk/app-debug.apk` (debug) or `app-release.apk` (release).

The app needs an online connection for sign-in, status changes, and notes. Queued background synchronization, photos, and push notifications are not implemented yet.
