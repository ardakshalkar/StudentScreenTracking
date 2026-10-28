# Student quick start

Your teacher supplies two things: a trusted **HTTPS classroom server address** and an **eight-character joining code**. Installing the extension alone does not create a classroom server.

**Trusted Wi-Fi HTTP option (1.0.2):** if your teacher specifically supplies a private-IP HTTP address such as `http://192.168.1.20:5173`, tick **Allow unencrypted HTTP on this Wi-Fi/LAN** before joining. The teacher must enable this mode on the server. Use name/ID and classroom code; Google sign-in is unavailable in LAN HTTP mode. Screenshots and credentials are unencrypted. All source-selection, acknowledgement and Stop controls below still apply. The Store draft is currently 1.0.1, so use the rebuilt 1.0.2 unpacked extension for this option until that package is uploaded and approved.

1. After publication, open the official Classroom Screen Sharing listing in Chrome Web Store, click **Add to Chrome**, review the permission prompt, and pin the extension. Before publication, follow your administrator's Load unpacked instructions instead. The store link will be added after Google creates/approves the listing.
2. Click the toolbar icon, then **Open sharing controls**. Keep that window and Chrome open throughout sharing.
3. Enter your teacher's exact HTTPS server address and classroom code. Click **Check classroom / join** and grant access to that server.
4. If school Google sign-in is required, click **Sign in with Google & join**. Use your approved school account. The server will reject other domains. For code-only classrooms, enter your name and student ID.
5. Read the disclosure, check the acknowledgement and close private content that might be visible in your selected source.
6. Click **Start Sharing**. Chrome's own picker opens. Choose the intended **screen** or **application window**, then confirm. There is no camera, microphone or audio capture.
7. Work in VS Code, Jupyter, PyCharm or your other application. Your teacher sees only the source you selected. Some minimized application windows stop updating; select the full screen if needed.
8. Watch the visible sharing and recording status. The teacher may enable periodic screenshot recording. Default interval: one changed screenshot every 20 seconds.
9. To stop immediately, click **Stop Sharing** in the extension window, its toolbar popup, or Chrome's sharing control. Closing the extension controls also stops capture.

A short network interruption can reconnect while the original capture permission is still active. An outage longer than 30 seconds stops capture; reconnect and deliberately start sharing again. Session end invalidates the old classroom code.

Do not enter a server address you do not trust. Ask your teacher/institution about access, retention and deletion of recordings. Removing the extension clears its local data but does not remove recordings already stored by the classroom server.
