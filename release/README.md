# Release 1.0.1

## Local update 1.0.2 · trusted-LAN HTTP

`classroom-screen-sharing-1.0.2.zip` and `classroom-server-source-1.0.2.zip` are the latest local builds, adding explicit code-only HTTP/WS on private IPv4 networks. Both client/server must opt in; screens and credentials are unencrypted. Use the new `scripts/start_lan.ps1` launcher and README instructions. Both client builds, 34 backend tests and 12 extension tests pass. The 1.0.2 package has **not** replaced the 1.0.1 Store draft. The existing video describes the HTTPS default and does not demonstrate LAN mode.

## Uploaded draft

The extension ZIP was accepted by Chrome Web Store and saved as **draft** `femgaepkcdhfebjcfpbgclhnmhffghnb`. It is **not yet submitted or public**. See `submission-status.json` for the verified state and outstanding Google requirements.

- `classroom-screen-sharing-1.0.1.zip`: extension-only upload package.
- `classroom-server-source-1.0.1.zip`: source-only teacher/server distribution for the owner to provide through a support site/repository; it has not been uploaded publicly. No `.env`, recordings or dependency directories are included.
- `classroom-screen-sharing-1.0.1.zip.sha256`, `package-report.json`: integrity and archive content inventory.
- `store-assets/`: icons, promo artwork, screenshot artwork and proof of the current submission blockers.
- `video/classroom-walkthrough.mp4`: narrated 1080p instructional guide, approximately 5m04s. Includes guided illustrations and an actual dashboard screenshot with synthetic test content. It does not claim real native screen capture was verified.
- `video/classroom-walkthrough.srt`: approximate narration subtitles for accessibility/video-host upload.
- `video/TRANSCRIPT.md`, `video/chapters.json`: text transcript and chapter timing.

Publisher copy/privacy worksheets and submission steps are in `../docs/store/`. Student/teacher guides are in `../docs/`. The same offline help/privacy pages ship inside the extension. Public policy/support URLs, publisher contact verification and data-use certifications remain necessary before Google allows submission. A functioning reviewer-accessible classroom environment and real hardware acceptance testing are also still required.

The MP4 has not been uploaded to YouTube or any other third-party video service. Its local file can be previewed and shared directly; publish it from the owner's chosen account if a hosted video URL is desired.
