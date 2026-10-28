# Teacher quick start

The extension is the student client. You run the backend **and** the teacher dashboard, either on a classroom computer/LAN or an HTTPS server. Full commands and Google configuration are in the project README.

**Wi-Fi without HTTPS (1.0.2):** activate your Python environment, install dependencies, set `TEACHER_PASSWORD` and `APP_SECRET`, find your Wi-Fi IPv4 address with `ipconfig`, and run `scripts/start_lan.ps1 -Address YOUR-PRIVATE-IP`. Open `http://YOUR-PRIVATE-IP:5173` on the teacher computer and give students the same address. They must enable **Allow unencrypted HTTP on this Wi-Fi/LAN** in the rebuilt 1.0.2 extension. The launcher enables server `ALLOW_LAN_HTTP=true`, code-only joining, and disables Google OAuth for this run. Traffic is unencrypted; use only a trusted classroom network. Allow the dashboard port on the private firewall profile if necessary and check Wi-Fi client isolation. Ctrl+C stops the launcher. See the README's LAN section for manual/Linux/macOS or Docker setup.

1. Install Python/Node for local development, or run `docker compose up --build -d` after configuring `.env`. Use a trusted HTTPS origin reachable from all student laptops.
2. Open the teacher website, sign in with the teacher password, and start a course/session. Give students its **server address** and **joining code**.
3. For school accounts only, configure `STUDENT_AUTH_MODE=google`, exact `STUDENT_ALLOWED_DOMAINS`, and student Google OAuth credentials. Omit `gmail.com` to exclude personal Gmail. Register the student callback at `/api/student-auth/callback`.
4. Ask students to install/open the extension, join, read the disclosure, and explicitly select a screen/window. The dashboard displays their actual images; no image appears before a student shares.
5. Search names/IDs, check connection status and last-frame timestamps, then click a thumbnail for focused quality. Close the enlarged view or press Escape to return to overview. At most two distinct students can be focused across teacher connections.
6. Recording starts **off**. If appropriate for the class, explain your policy, enable periodic screenshots, and set the interval. Live monitoring stays independent of recording. Default: every 20 seconds; changed screens only.
7. Open **Playback** to review saved screenshots by student and timestamp. Optional teacher Google Drive OAuth uses the separate `/api/drive/callback`; uploads are ZIP batches, not individual images.
8. End the classroom after the lesson. Connected captures stop, and students cannot rejoin with the expired code. Archive batches seal for optional upload.

For two laptops on one network, students use the teacher computer's trusted HTTPS hostname/address. `localhost` points to each student's own computer. Permit the server through its firewall and check Wi-Fi client isolation. Local code-only sharing/recording can work without internet after setup; Google login and Drive require internet.

Before use, perform a real two-device capture test on your OS, including application switching, Chrome Stop Sharing, extension Stop Sharing, session end and network recovery. Know who can access the data. Set `RETENTION_DAYS` to the approved policy; default screenshot retention is 30 days. Identity metadata remains until the operator removes it. The supplied backend supports one teacher account and one process; add institutional identity/authorization before expanding to multiple teachers.
