# Verification scope

## LAN HTTP update · 25 October 2026

Local extension/server version 1.0.2 adds opt-in private-IPv4 LAN HTTP/WS with code-only joining and visible unencrypted-transport disclosure. Both client builds passed; 34 backend tests and 12 extension tests passed. Tests verify private-address boundaries, default rejection without opt-in, rejection of Google/Drive OAuth on a LAN HTTP origin, teacher login/cookie/Origin checks and authenticated student/teacher sockets. The Windows LAN launcher passed PowerShell syntax parsing. A real two-laptop Wi-Fi and native screen-capture test remains pending; no such test is claimed. The Chrome Web Store draft and its verified upload hash remain version 1.0.1; the local 1.0.2 ZIP has not been uploaded.

Results from this Windows development environment on 2026-10-24. This file distinguishes protocol tests from real OS capture.

## Automated

| Check | Result |
| --- | --- |
| `npm run build` | PASS: React/Vite production bundle and Manifest V3 extension bundle; both strict TypeScript checks passed |
| `python -m pytest backend/tests -q` | PASS: 24 tests, covering the original 11 recording/transport/Drive checks plus Google student identity, exact domain enforcement, managed Workspace identity, Gmail, rejected legacy socket credentials, OAuth state/nonce/PKCE, single-use exchange, and classroom binding |
| `npm run test:extension` | PASS: 9 tests against actual TypeScript transport and Google sign-in classes with mocked browser APIs/clock; includes redirect/state rejection and PKCE grant binding |
| Playwright in installed Chrome | PASS: image rendering, search, focus, recording, playback, and session end; synthetic image delivered through the real student/teacher protocol |
| `python scripts/run_load_test.py` | PASS: 30 students; 279 transmitted frames / 279 teacher frames; minimum 8 frames per student; 14.29 MB; focus activated; 56 recorded samples; 28.95s total including startup/join |
| `docker compose config --quiet` | PASS with test configuration environment values |
| Docker runtime | Not run: installed Docker CLI, Docker engine is not running |

The load test generated 25 seconds of synthetic screen activity. It was run against an actual temporary Uvicorn server, including authenticated HTTP joins, student binary WebSockets, teacher image delivery, and screenshot recording. It does not prove cross-platform native capture or network capacity outside this computer. The browser screenshot is saved locally at `artifacts/dashboard-browser-test.png` and explicitly labels its image as synthetic test traffic. No synthetic thumbnail path is present in the production dashboard.

## Requires an interactive acceptance test

- Load `extension/dist` into actual Chrome, explicitly select a screen/window in its native picker, and confirm that source appears on the teacher website. No OS picker interaction is claimed by automated tests.
- Test Windows, macOS (including Screen Recording system permission), and Linux/Wayland capture behavior on the deployment hardware.
- Complete real teacher Google OAuth and inspect uploaded archives in the teacher's Drive account.
- Configure student Google OAuth and the domain allowlist, reload the extension, and complete a real allowed-school-account sign-in. Verify an unapproved account is rejected and its screen cannot connect. The automated Google flow tests use mock Google responses/verifiers; real Google consent is not claimed.
- Run the documented two-laptop HTTPS/WSS test, including source-window closure, application switching, network interruptions, session end, and stop controls.
- Build/run Docker Compose on a Docker-enabled machine and validate trusted certificates/DNS for the chosen hostname.

## Store release work

Extension version 1.0.1 adds icons, bundled help/privacy pages, and an explicit sharing-disclosure acknowledgement before Chrome source selection. The extension ZIP was validated and uploaded to Chrome Web Store as draft `femgaepkcdhfebjcfpbgclhnmhffghnb`. Listing assets and factual privacy/permission fields were saved. The draft is not submitted or public; `release/submission-status.json` records Google's exact outstanding fields.

After these changes, both client builds/type checks, 24 backend tests and 9 extension transport/Google-auth tests passed. The upload ZIP is 24,368 bytes and contains no `.env`, backend code, dependencies or source maps. The narrated video is an instructional guide using illustrations and an actual screenshot of synthetic dashboard test traffic; H.264 1920×1080 at 24 fps, AAC narration, 303.92 seconds, approximately 5.7 MB. FFmpeg decoded the audio successfully and measured audible narration without clipping (mean -20.6 dB, peak -2.4 dB). Prepared scene images were visually inspected. This work does not claim a completed real native-capture acceptance test.

Follow the detailed procedures in README.md. Real screen-capture permission dialogs must be accepted by a person; tests do not bypass them.
