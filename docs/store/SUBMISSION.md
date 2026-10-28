# Publish Classroom Screen Sharing

## Prepared assets

Build with `python scripts/release_assets.py`, `npm run build`, then `python scripts/package_extension.py`. The upload file is `release/classroom-screen-sharing-1.0.1.zip`. Its manifest is at the ZIP root; source maps, server code, `.env`, credentials and dependencies are excluded. Check `release/package-report.json` and the SHA-256 file.

Artwork is in `release/store-assets`: 128px store icon, 440×280 optional promotional tile, 1400×560 optional marquee, and 1280×800 listing artwork. Screenshot artwork uses an actual dashboard screenshot with clearly labeled synthetic classroom content. The instructional video is a guided walkthrough, not a proof of native capture.

`python scripts/package_server.py` prepares `release/classroom-server-source-1.0.1.zip`, a source-only teacher/server distribution without `.env`, recordings, dependency directories or logs. Host that bundle or a source repository from the support site so other teachers can actually obtain/run their server. The local bundle has not been published anywhere yet. Decide the distribution/license terms before public source distribution; no license has been invented for the owner.

## Dashboard steps

1. Sign into the [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole). If necessary, register the publisher and complete Google's required verification/registration steps yourself. Review any fees and agreements before accepting them.
2. Choose **Add a new item**, upload the ZIP and wait for validation. Creating this draft allocates the extension's permanent store item ID. Do not reuse the unrelated old boilerplate draft in the account.
3. Use `LISTING.md` for copy and upload the prepared icons/screenshots. Use the actual public publisher/support details supplied by the owner.
4. Publish the support/help and privacy pages at stable public HTTPS URLs, then enter those URLs. The app includes the same pages at `/help.html` and `/privacy.html`, but a localhost/private server URL is not a public policy host.
5. Complete the privacy fields using `PRIVACY_FIELDS.md`, reviewing each statement before certification. This extension transmits screens and identity; do not select “collects no user data.”
6. For distribution, choose the owner's intended audience (public for broad availability, or unlisted for initial limited rollout). Prepare a reviewer-accessible classroom server and a repeatable test path. A Google-domain-only mode needs an allowed test account; code-only staging can simplify review if that accurately matches the submitted behavior.
7. Add the allocated extension ID to production `EXTENSION_IDS`; reload/restart the backend. Student Google OAuth redirects through the backend callback, so keep the correct backend student OAuth redirect URI registered. Avoid confusing the teacher's Drive callback with the student's sign-in callback.
8. Install the actual package using Load unpacked and complete a real two-device test: Google/code join, native screen picker, application switching, readable teacher focus, Stop controls, recording/playback, classroom end and connection recovery. Test each intended OS. Automated/synthetic traffic does not replace this step.
9. Resolve all missing dashboard fields and reviewer notes. Submit for review only when the listing, public policy, test server and behavior are accurate. Google decides acceptance and timing; a draft upload is not a public installation link.
10. After approval, verify the public listing and installation. Add the real Store URL to the help pages, student guide and video description. Upload the MP4 to the owner's video account if a hosted video link is desired.

## Publication status for this work

See `release/submission-status.json` for the most recently verified dashboard state. Do not describe the extension as published until its live listing has been verified.

## Official references checked on 24 October 2026

- [Publish an extension](https://developer.chrome.com/docs/webstore/publish/)
- [Required/optional images and sizes](https://developer.chrome.com/docs/webstore/images/)
- [Privacy fields and permission justifications](https://developer.chrome.com/docs/webstore/cws-dashboard-privacy/)
- [Chrome Web Store program policies](https://developer.chrome.com/docs/webstore/program-policies/policies/)
