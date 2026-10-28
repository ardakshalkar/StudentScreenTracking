# Chrome Web Store privacy declarations

The publisher must review these against its actual deployment and Google dashboard wording before certifying them. This is a release worksheet, not a claim that certification has already been submitted.

## Single purpose

Allow a student to explicitly share a selected screen/application window with the authenticated teacher of the active classroom they join, including related identity verification, stream status, and optional periodic screenshot recording.

## Permissions

**desktopCapture**: Displays Chrome's native screen/window picker after the student's Start Sharing action. The selected source is captured only for that classroom. Audio sources, camera and microphone are not requested.

**storage**: Saves the student's chosen classroom server, name/ID and application-scoped student credential locally so they can reconnect and deliberately restart sharing. It does not store the teacher's Google credentials.

**identity**: Opens Google's interactive sign-in flow when the selected classroom requires approved-domain Google student login. Validated identity is used for joining the classroom. It does not access browser history or teacher Google Drive credentials.

**Optional host access (`http://*/*`, `https://*/*`)**: Different institutions host different classroom servers, so the server cannot be hardcoded. The extension requests access at runtime for the specific origin the student enters. HTTPS/WSS is the default. Version 1.0.2 adds an explicit private-IPv4 LAN HTTP/WS option, requiring both server opt-in and a student checkbox with an unencrypted-traffic disclosure; it supports code-only joining. HTTP loopback is also available for development. Access is used for join/auth/status requests and live transport to that selected institution. The extension has no content scripts or background browsing access. Optional wildcard declarations can receive additional review; for a single-school release, narrow them to that school's actual origin before packaging instead. The uploaded 1.0.1 draft does not yet contain the LAN option; update its package, listing and disclosures together when uploading 1.0.2.

## Remote code

No remote executable code. All extension scripts are bundled locally. Google OAuth pages are external sign-in pages in Chrome's identity flow, not remotely injected extension code. Server responses are treated as data/control messages, not scripts.

## User-data categories to disclose

- **Personally identifiable information**: name, student ID, verified email/profile/account identifier in Google mode, and server-side network/request metadata such as IP addresses.
- **Authentication information**: application session credentials and Google authorization/sign-in processing on the backend. Google access/ID tokens from student sign-in are discarded after verification; teacher Drive refresh credentials are stored encrypted by the backend only.
- **Location**: the dashboard's category explicitly includes IP addresses; a classroom server receives normal network/request IP metadata. The extension does not request GPS/geolocation access.
- **User activity**: selected screen/window activity and capture health are transmitted for the disclosed classroom monitoring purpose. The extension does not log click coordinates, keystrokes, clipboard contents or browsing history through browser APIs.
- **Website content**: screenshot contents, including visible text/images and possible personal information in the selected source. The extension captures windows/screens outside the browser too. Disclose this explicitly in free-text descriptions even if the dashboard uses a browser-content label.
- Review any categories for sensitive content intentionally captured in the planned deployment. Do not falsely certify that screenshots can never include financial, health, private communications or other sensitive information. The extension has no APIs for separately collecting those records, but a student-selected screen may show them.
- Do not claim browser history/keystroke/clipboard API collection; no such feature is implemented.

## Limited use

Confirm the data is used for the disclosed classroom sharing/related recording purpose; not sold, not used for advertising, not used for unrelated profiling or lending/credit decisions. The public policy includes the Google APIs/Chrome Web Store Limited Use statement. The publisher remains responsible for its own actual practices and the accuracy of the certification.

## Before submission

Publish an accurate public privacy-policy URL and support contact; check consent/disclosure in the actual extension; run a real capture test; provide reviewers an accessible test server and credentials/instructions. Neither a private LAN address nor localhost on the publisher's laptop is accessible to a remote Google reviewer.
