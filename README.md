# Classroom Screen Sharing

A Chrome Manifest V3 student extension, a React teacher dashboard, and a FastAPI backend. Students use **only the extension**; teachers use **only the website**. There is no `/student` capture page and no native application.

## Store release and instructions

Version **1.0.1** has been uploaded as a Chrome Web Store **draft**, item ID `femgaepkcdhfebjcfpbgclhnmhffghnb`. It is not yet submitted, approved or publicly installable. See [submission instructions](docs/store/SUBMISSION.md) and `release/submission-status.json` for the verified state and remaining requirements. Add this store ID to production `EXTENSION_IDS` when deploying the Store build.

- [Student instructions](docs/STUDENT_GUIDE.md)
- [Teacher instructions](docs/TEACHER_GUIDE.md)
- Public-ready help/privacy pages: `web/public/help.html` and `web/public/privacy.html`, also bundled inside the extension. They still need a stable public host for the Store privacy-policy URL.
- Narrated guided video: `release/video/classroom-walkthrough.mp4` (approximately 5 minutes, 1080p), plus `.srt`, `TRANSCRIPT.md`, and `chapters.json` in the same folder. It uses illustrations/sample content and an actual dashboard test screenshot; it is not a native-capture acceptance test or a claim that the extension is already published.
- Rebuild the upload ZIP with `npm run release:extension`. Generate video scenes with `python scripts/build_walkthrough.py prepare`, narrate on Windows with `scripts/narrate_walkthrough.ps1` (Microsoft Zira voice), then run `python scripts/build_walkthrough.py encode` (FFmpeg required). On another OS, provide equivalent scene WAV files before encoding. Media scripts use Pillow from the backend dependencies.

The extension now requires a sharing acknowledgement before opening Chrome's picker and includes offline instructions/privacy links. The submitted package excludes server files, credentials, dependencies, and source maps. Publishing the extension does not host the backend/dashboard or eliminate teacher server setup.

The supplied workspace was empty, so this implementation establishes the requested components rather than migrating pre-existing code. Single teacher account, one active classroom at a time, up to 35 students, and two distinct focused streams across all teacher tabs. Run **one backend worker/replica**: live frames, focus leases, and WebSocket connections are process-local. SQLite and ZIP archives persist on disk.

## Quick start (Windows PowerShell)

Requirements: Python 3.11+, Node 22.12+ (or Node 20.19+), current Chrome.

## Wi-Fi / LAN over HTTP (version 1.0.2)

Students and teacher can use the same trusted Wi-Fi without certificates using the explicit **LAN HTTP** option. This is opt-in on both sides and accepts only private IPv4 addresses (`10.x.x.x`, `172.16`–`172.31.x.x`, `192.168.x.x`). Public HTTP addresses, arbitrary hostnames, and IPv6 HTTP LAN addresses are not enabled by this mode. Screenshots, student credentials and teacher passwords are **unencrypted on the network**; use HTTPS for secure deployments. Authentication, session codes, teacher Origin checks and Chrome's capture permission picker remain required.

On the teacher's Windows computer, after installing the dependencies from Quick start:

```powershell
ipconfig
# Copy the active Wi-Fi adapter's IPv4 address. Replace the example below.
$env:TEACHER_PASSWORD = 'choose-a-unique-password-at-least-12-characters'
$env:APP_SECRET = (python -c "import secrets; print(secrets.token_urlsafe(48))")
.\scripts\start_lan.ps1 -Address 192.168.1.20
```

The launcher starts the backend on loopback and the Vite dashboard/proxy on the LAN. Open **`http://192.168.1.20:5173`** in the teacher browser, and give students that exact address plus the joining code. The teacher must use that LAN address too: logging in through localhost would fail the configured Origin check. Stop the launcher with Ctrl+C when finished. It restores its environment overrides and stops the backend it started. Use `-Port 5180 -BackendPort 8013` if the defaults are occupied. The teacher password/secret remain environment settings; keep APP_SECRET stable to preserve existing encrypted/authenticated configuration across runs. The launcher temporarily disables Google sign-in and Drive OAuth for this run and restores previous environment values afterwards.

On each student laptop, rebuild/reload the **1.0.2** unpacked extension, enter the same HTTP address, tick **Allow unencrypted HTTP on this Wi-Fi/LAN**, enter name/ID and classroom code, then join and explicitly select a source. The LAN checkbox is not remembered automatically. The backend's `ALLOW_LAN_HTTP=true` and `STUDENT_AUTH_MODE=code` must agree with the student's choice. Current Chrome/OS versions may request local-network access; grant it only for your intended classroom server. This extension still requests host access only for the entered origin.

Permit TCP **5173** through Windows Firewall for the **Private** network if needed (or the port you selected); do not disable the firewall or expose this demo server to the internet. Check school/guest Wi-Fi client isolation if laptops cannot reach one another. Backend port 8000 stays on loopback with the launcher; only the web proxy needs LAN access. Put a DHCP reservation on the teacher's address or update `PUBLIC_ORIGIN` and student URLs when it changes.

For manual startup or macOS/Linux, set `PUBLIC_ORIGIN=http://YOUR-PRIVATE-IP:5173`, `ALLOW_LAN_HTTP=true`, `STUDENT_AUTH_MODE=code`, disable Google Drive credentials, and run the usual Uvicorn command on loopback. In another terminal run `npm run dev -- --port 5173` (the existing dev script binds the Vite server to all interfaces). Use `export NAME=value` instead of PowerShell environment syntax. Docker can also use `PUBLIC_ORIGIN=http://YOUR-PRIVATE-IP`, `SITE_ADDRESS=http://YOUR-PRIVATE-IP`, `ALLOW_LAN_HTTP=true`, and `STUDENT_AUTH_MODE=code` with Drive OAuth disabled; its mapped HTTP port is 80. Google student sign-in and connecting Google Drive require the HTTPS setup instead of LAN HTTP.

The Store draft remains version 1.0.1. The local 1.0.2 ZIP and its revised help/privacy pages are prepared separately; they have not replaced the uploaded draft. The existing narrated video documents the HTTPS default and does not demonstrate this newly added LAN option.

### Standard HTTPS / loopback development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
npm ci
npm run build

$env:TEACHER_PASSWORD = 'choose-a-unique-password-at-least-12-characters'
$env:APP_SECRET = (python -c "import secrets; print(secrets.token_urlsafe(48))")
$env:PUBLIC_ORIGIN = 'http://localhost:5173'
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1 --ws-max-size 1100000 --ws-max-queue 1
```

In a second terminal, run `npm run dev` and open [the teacher dashboard](http://localhost:5173). Log in with `TEACHER_PASSWORD`. Start a session with a course and title. Recording starts **off**; enable it explicitly in the session controls.

For macOS/Linux, activate with `source .venv/bin/activate`, and set environment variables using `export NAME=value`. All Python commands run from the repository root. Local development reads environment variables from the shell; it does **not** automatically load `.env`. Docker Compose reads `.env` automatically.

## Build and install the extension

1. Run `npm ci`, then `npm run build -w extension` (or `npm run build` for both clients).
2. Open `chrome://extensions`, enable **Developer mode**, and choose **Load unpacked**.
3. Select this project's **`extension/dist`** directory. Pin **Classroom Screen Sharing** to the toolbar.
4. Click the extension, then **Open sharing controls**. A dedicated extension window opens.
5. Enter the server origin (`http://localhost:5173` locally, or your deployed `https://…` origin), name, student ID, and the teacher's eight-character code.
6. Click **Join classroom** and grant access to that server. This is an optional host permission for the selected server only.
7. Click **Start Sharing**. Chrome opens its screen/window picker. Explicitly select a source and confirm.
8. Switch to VS Code, Jupyter, PyCharm, or another application. Keep the extension control window and Chrome open. The chosen source continues sharing while available.
9. Click **Stop Sharing** in the extension window or toolbar popup, or use Chrome's sharing control. Closing the sharing window also stops capture.

Name, ID, and server are remembered locally. A student-scoped session credential is also stored locally for reconnection and deliberate restarts in the same classroom. Nothing starts capture automatically after a restart. In code-only mode an ID cannot be claimed twice in one session; resume from the original extension profile. If that profile's credential is lost or expires, the teacher can start a new classroom or the student can join under a distinct ID. In Google mode, signing in again resumes the same verified email's student entry. Tokens and teacher logins expire after 12 hours. Do not reuse the same installation/profile simultaneously for multiple students.

## Student Google sign-in and allowed domains

To require Google sign-in and allow only specified student domains, configure the backend:

```dotenv
STUDENT_AUTH_MODE=google
STUDENT_ALLOWED_DOMAINS=school.edu,students.school.edu
STUDENT_GOOGLE_CLIENT_ID=your-web-application-client-id.apps.googleusercontent.com
STUDENT_GOOGLE_CLIENT_SECRET=your-client-secret
```

Use your institution's actual domains. Matching is **exact**, case-insensitive, and enforced on the backend for both joining and student WebSocket authentication. Subdomains must be listed separately. Wildcards, `@`, URLs, and an empty allowlist are rejected on startup in Google mode. Setting `STUDENT_AUTH_MODE=code` retains the original code/name/ID flow for development; configuring domains alone does not enable enforcement. The Compose file passes all four settings through. For local Python development, set the same values as shell environment variables before starting Uvicorn.

Create a Google OAuth **Web application** client and register `https://YOUR-HOST/api/student-auth/callback` as an authorized redirect URI (or `http://localhost:5173/api/student-auth/callback` for loopback development). Student sign-in requests only `openid email profile`. These settings are separate from the teacher's Google Drive OAuth credentials; student login does not require enabling Drive, granting Drive scopes, or setting the Drive token encryption key. Google Cloud consent-screen testing mode also requires adding student accounts as test users. Configure the consent audience to match whether you allow only your Workspace organization or accounts across several organizations.

Rebuild the extension and click **Reload** at `chrome://extensions` after this update, since the manifest now includes the Chrome `identity` permission. The student enters the server URL and classroom code, clicks **Check classroom / join**, then **Sign in with Google & join**. The extension shows allowed domains and the verified account. Manual name/ID fields are hidden for Google classrooms. The teacher dashboard and recordings use the Google profile name and **verified email as the student ID**; a client cannot override them. The student still explicitly clicks **Start Sharing** and selects a screen/window after signing in.

The backend validates Google's signed ID token (signature, issuer, audience, expiry, and nonce), then checks the allowlist. For school domains it also requires the Google Workspace `hd` claim to equal the email domain, following [Google's identity verification guidance](https://developers.google.com/identity/openid-connect/reference). This rejects consumer Google accounts merely claiming an address in the school's domain. Workspace alias domains whose `hd` differs from the email domain are deliberately rejected; use the student's managed primary-domain account. To allow personal Gmail accounts, add `gmail.com`; that admits **any verified Gmail account** with a valid classroom code. Omit `gmail.com` to keep personal Gmail accounts out.

Google's picker opens through Chrome's [identity API](https://developer.chrome.com/docs/extensions/reference/api/identity). The server OAuth callback returns to the initiating extension's `chromiumapp.org/student-login` URL with a 60-second single-use grant. A separate PKCE challenge binds that grant to the initiating extension, while the Google authorization-code exchange has its own PKCE challenge, state and nonce. Google access/ID tokens are discarded on the backend after verification. Students receive only application-scoped credentials. Teacher Drive credentials and permissions remain separate. Google-mode startup fails if credentials or the allowlist are missing; existing code-only tokens cannot authenticate Google-mode student sockets.

Automated tests mock Google's external token exchange/verifier to exercise the sign-in flow, nonce/state/PKCE protections, grant replay rejection, domain rejection, verified identity mapping, classroom binding, and legacy-token denial. Completing an actual Google consent/sign-in flow requires your configured OAuth client and a real test account.

The capture owner is a **persistent extension page/window**, not the transient toolbar popup or service worker. The picker and `getUserMedia()` execute in the same document. This follows Chrome's [desktopCapture API](https://developer.chrome.com/docs/extensions/reference/api/desktopCapture) and its [extension page capture approach](https://developer.chrome.com/docs/extensions/how-to/web-platform/screen-capture). There is no service worker whose suspension can kill the capture pipeline. No content scripts, external native hosts, camera, microphone, or audio permissions are requested. The only picker sources are `screen` and `window`; `audio: false` is explicit. macOS may additionally require granting Google Chrome screen-recording access in system settings and restarting Chrome. Window capture of minimized/closed windows and Linux Wayland portal behavior depend on the OS/compositor; share the full screen when window capture stops updating. Test on each OS you deploy to.

## Live viewing and focus

- Overview: 640px wide (bounded by source aspect ratio), WebP quality .68, every 2.5 seconds. A second .48-quality encode attempts to bring complex overview frames toward 60 KB; 20–60 KB is a target, not a guaranteed size. Simple screens may be smaller, complex screens larger.
- Focus: click a student card. The backend requests approximately 1600px / 3 fps / .90 quality. Close the enlarged view or press Escape to return to overview. At most **two distinct students** can be focused across teacher connections. A 15-second teacher heartbeat lease also clears abandoned focus requests.
- A small pixel comparison suppresses visually unchanged frames. A five-second capture-health heartbeat distinguishes quiet screens from disconnected capture pipelines. The UI shows the last image timestamp even while a healthy screen is unchanged. A pipeline without capture progress for 15 seconds is marked frozen; loss of connection/heartbeat is marked disconnected.
- One unacknowledged frame per extension, low WebSocket `bufferedAmount` threshold, and no screenshot FIFO. On reconnect, the newest authorized screen is captured again. Backend stores one latest frame per student; slow teacher sockets read current frames rather than a growing history. Use the documented Uvicorn queue/size limits.
- Reconnect uses the existing student credential and already-authorized media stream. It never opens a picker silently. Server messages renew a **30-second capture lease**. A longer outage stops capture; the student must deliberately restart it. Session end stops connected students immediately and prevents reconnect/join. A disconnected extension stops when its lease expires.

The dashboard renders only images received over authenticated student WebSockets. It contains no simulated thumbnails. Synthetic images exist only in the explicit load-test script.

## Recording, archives, and playback

Live monitoring works with recording disabled. Default recording interval is **20 seconds**; the teacher can choose 5–3600 seconds. Only changed screenshots are sampled, normalized independently of focus mode, recompressed as WebP, and written directly to disk. It never records continuous video. Thirty students at 20 seconds produce at most 90 samples/minute before unchanged-screen suppression.

Each student gets ZIP batches spanning at most five-minute time buckets, sealing early at 4 MB. Batches contain WebP images plus JSON with student ID, session ID, and the server's UTC Unix receipt timestamp. SQLite indexes individual images for authenticated playback. Only the latest live image per student is held in memory; recording and upload have no unbounded in-memory queues. ZIP images are already compressed and use ZIP_STORED. Current batches seal on size limit, time-bucket change, or session end; sealed archives are eligible for Drive upload. The actual image receipt time is preserved; this is a periodic screenshot timeline, not video playback. Playback previews advance one saved sample per second and display original timestamps.

Click **Playback** or **Session recordings**, select a student, then use Play or scrub the screenshot timeline. Recordings are served by authenticated endpoints; data files are never exposed as a static directory. The UI currently lists up to 20,000 samples per session. Short classrooms stay well below this; paginate this API before using unusually long recordings.

Set `RETENTION_DAYS` (default **30**) on the backend to automatically remove local images and their playback indexes. The worker runs every 30 seconds. Uploaded copies are deleted from Drive too, with retries if Google is unavailable. Local deletion still runs when OAuth is broken; pending remote deletion metadata is retained. Student/session identity metadata stays in SQLite for classroom history. Protect/backup the data directory as appropriate for your institution. Use host disk encryption if you require encrypted local screenshot storage. A backend restart closes all active classrooms and seals archive batches; teachers create a new classroom after restart.

## Optional Google Drive

The system works normally without Google configuration. Live viewing, recording, local archives, and playback do not depend on Drive.

1. In Google Cloud, enable the **Google Drive API**, configure the OAuth consent screen, and create an OAuth **Web application** client.
2. Register this exact authorized redirect URI: `https://YOUR-HOST/api/drive/callback`. For Vite-only local development Google also allows `http://localhost:5173/api/drive/callback`.
3. Set backend `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `TOKEN_ENCRYPTION_KEY`. Generate the encryption key:

   ```powershell
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. Restart the backend, sign into the teacher website, and click **Connect Google Drive** in the footer. Authorize as the teacher. For Google's testing consent mode, add the teacher as a test user; testing-mode grants may expire and need reconnection.
5. Enable recording, share a changing screen, and end the session to seal batches. The uploader picks them up within about 30 seconds. Refresh the dashboard to reload the footer's pending count/status.

The OAuth callback validates a single-use, ten-minute state token. Only the backend receives authorization/refresh tokens. Refresh tokens are Fernet-encrypted in SQLite; keep the encryption key stable and secret. The extension receives only its student-scoped classroom credential, never Google secrets. The restricted `drive.file` scope manages only files created/authorized by this application.

Archives are organized as **Classroom Screens / Course / Session title + ID / Student ID + ID / batch.zip**. Uploads stream from disk using `multipart/related`. A Drive-generated file ID is saved before upload. A retry checks/reuses that same ID, preventing duplicates even if the original success reply was lost. Failed uploads have durable exponential retry metadata (up to one hour between retries). Expired recordings are deleted rather than uploaded later. Actual OAuth and Drive-account operation require teacher credentials; automated tests use a mock Google transport for upload failure/idempotency and encryption behavior.

## Two-laptop test and HTTPS/WSS deployment

For the secure default, use a DNS hostname reachable from both laptops with a trusted TLS certificate; remote WebSockets use **WSS**. Version 1.0.2 also supports the explicit trusted-LAN HTTP/WS option documented above. `localhost` on laptop B points to B, not laptop A. Avoid self-signed certificates that Chrome does not trust.

1. Copy `.env.example` to `.env`. Generate a random `APP_SECRET`, choose a strong teacher password, and set `PUBLIC_ORIGIN=https://classroom.example.edu` and `SITE_ADDRESS=classroom.example.edu`.
2. Point DNS to your server. Allow inbound TCP 80/443 and optionally UDP 443. Docker Compose exposes only Caddy; the backend is private on the Compose network.
3. Run `docker compose up --build -d`. Caddy obtains/renews TLS automatically for a public DNS hostname and proxies HTTP/WebSockets to the backend. Persistent named volumes keep SQLite, archives, and certificates.
4. For local Docker development the defaults use `https://localhost`; Caddy uses a local CA. Trust its root CA on the test computer, or use the Python/Vite HTTP loopback quick start instead. Public DNS TLS is easier for two laptops. Do not use HTTP LAN addresses in the extension.
5. On laptop A, open the website, log in, and create a classroom. On laptop B, load the extension, enter the same HTTPS origin and classroom code, then select an actual screen/window.
6. Confirm the real screen appears on A. Edit code on B; click its card on A; verify readable enlarged updates. Close the enlarged view and check that the extension reports Overview again.
7. Enable recording with a five-second interval for this test. Make several visible edits. End the classroom and open Playback. Confirm changed screenshots and timestamps.
8. Test Chrome's Stop Sharing control, extension Stop Sharing, closing the selected window, and closing the sharing controls. Verify capture/transmission stop. End the classroom while sharing; verify the extension stops and cannot rejoin the old code.
9. Interrupt B's network briefly and restore it within 30 seconds: sharing should recover using the existing permission. For a longer interruption, verify capture stops and requires Start Sharing again.
10. Configure Drive if desired, end a recorded session, and confirm one ZIP per student/batch instead of individual image uploads. Verify playback and retention with your institution's policy.

Set `EXTENSION_IDS` to the comma-separated unpacked or managed extension IDs shown at `chrome://extensions` for production. Each unpacked installation may have a different ID. Keep joining codes within the classroom; the code is a join credential, not proof of a student's real-world identity. The application has one teacher account; use institutional identity integration before opening it to multiple teachers. Credentials travel in HTTPS requests or the first authenticated WSS message, never URL query parameters. Teacher authentication uses an HTTP-only, SameSite cookie; modifying teacher requests also validate the exact public Origin. Caddy sets browser security headers. Apply institutional consent and access policies before classroom use.

## Automated validation

```powershell
npm run build
python -m pytest backend/tests -q
npm run test:extension
npm run test:ui
python scripts/run_load_test.py
```

The load runner starts a temporary isolated backend on localhost:8011, authenticates a teacher, joins 30 synthetic students, transmits real encoded WebP payloads for 25 seconds, consumes them through the actual teacher WebSocket, requests focus, and checks recording. It always ends its test session and terminates its server. The report labels the traffic synthetic; it does not exercise OS screen permissions. Its data is temporary, and backend logs go to `load-server.log` (ignored by Git). Change duration with `--seconds 60` or student count with `--students 30`. To target a separately running **empty test server**, set `TEACHER_PASSWORD` and run `python scripts/load_test.py --url https://your-test-host`; it creates and ends a test classroom.

Tests cover authenticated frame delivery, session codes, capture authorization scope, focus changes, periodic recording, ZIP deduplication, playback access, reconnects, invalid image rejection, token expiry, encryption, and idempotent Drive upload recovery. Extension transport tests exercise the actual TypeScript connection class with a mocked WebSocket and clock: ACK backpressure, reconnection, fatal authorization errors, and offline capture lease expiry. The Playwright test launches installed Chrome (channel `chrome`) and temporary backend/Vite servers on ports 8012/5179; it verifies actual dashboard image rendering, search, focus, recording, playback, and classroom shutdown using an explicitly synthetic image sent through the real authenticated student protocol. `npm run test:ui` requires Chrome installed, or change the Playwright channel to a browser available on your machine. Backend tests use local event-loop sockets even in TestClient; restricted sandboxes may need local socket access. [Verification notes](VERIFICATION.md) record what was exercised and what still requires a person and hardware.

## Project layout

| Path | Purpose |
| --- | --- |
| `extension/src/popup.ts` | Toolbar popup; opens/focuses capture controls and stops sharing |
| `extension/src/session.ts` | Persistent extension capture owner and recording status UI |
| `extension/src/auth.ts`, `config.ts` | Join credentials, remembered identity, server configuration |
| `extension/src/capture.ts` | Explicit Chrome desktop picker and screen/window media stream |
| `extension/src/compression.ts`, `quality.ts` | Bounded image resize, WebP encode, unchanged suppression |
| `extension/src/connection.ts` | ACK backpressure, heartbeats, capture lease, reconnect recovery |
| `web/src/main.tsx` | React teacher dashboard, sessions, focus, recording, playback |
| `backend/main.py`, `security.py` | FastAPI endpoints, authenticated WebSockets, live state |
| `backend/storage.py`, `drive.py` | SQLite index, batched ZIP recording, OAuth/upload/retention |
| `scripts/` | Explicitly synthetic 30-student transport test |
| `deploy/`, `compose.yaml` | Same-origin production build and TLS reverse proxy |
