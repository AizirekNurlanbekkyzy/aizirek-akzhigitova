# FixFlow Android technician app

The Flutter app provides a technician sign-in, assigned work list, request details (address and preferred visit time), accept/start/complete actions, and shared request notes. Access tokens are stored with Android secure storage. It connects to the existing FixFlow API; the app does not use mock requests.

## Generate the Android wrapper

Install Flutter and Android Studio with the Android SDK, then from this directory run:

```powershell
flutter create --platforms=android --org=com.fixflow .
flutter pub get
```

Keep the existing `lib/` and `pubspec.yaml` when Flutter asks about files that already exist. In `android/app/src/main/AndroidManifest.xml`, set `android:usesCleartextTraffic="true"` on the `<application>` element for local HTTP development and set `android:allowBackup="false"` to protect secure-storage keys. For a deployed service, use HTTPS instead of cleartext HTTP.

## Run on Android

For the Android emulator, the default API address is `http://10.0.2.2:8001/api/v1`. Pass the demo organization ID printed by the seed command (or use the app's organization field):

```powershell
flutter run --dart-define=DEFAULT_ORGANIZATION_ID=<organization-id>
```

For a physical phone, put the computer and phone on the same trusted Wi-Fi, set `HOST_BIND=0.0.0.0` in the ignored project `.env`, allow the API port through Windows Firewall on the private network, and pass the computer's LAN IPv4 address:

```powershell
flutter run --dart-define=API_BASE_URL=http://<computer-lan-ip>:8001/api/v1 --dart-define=DEFAULT_ORGANIZATION_ID=<organization-id>
```

Build a release APK with:

```powershell
flutter build apk --release --dart-define=API_BASE_URL=https://<your-api-host>/api/v1 --dart-define=DEFAULT_ORGANIZATION_ID=<organization-id>
```

The APK is written to `build/app/outputs/flutter-apk/app-release.apk`. The app requires an online connection for sign-in, refresh, status changes, and notes; queued background synchronization, photos, and push notifications are not implemented yet.
