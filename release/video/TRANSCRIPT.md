# Classroom Screen Sharing · narrated walkthrough

Guided illustrations and a real dashboard test screenshot; sample content. Not a native capture acceptance test.

## A window into your classroom.

Welcome to Classroom Screen Sharing. Teachers use a website, and students use a Chrome extension. Your teacher or institution must run the classroom backend and dashboard. Installing the extension alone does not create a hosted classroom. This guided demonstration uses sample content and illustrations, not a recording of an accepted native screen capture dialog.

## 1. Prepare the classroom server

Teachers first start the backend and dashboard using the project instructions. Give the server a trusted HTTPS address reachable from student laptops. Sign into the teacher website and create a course and session. Share the server address and the eight character classroom code. The same Wi-Fi network can be used, but localhost on a student laptop points to that student laptop, not to the teacher.

## 2. Install and open the extension

After the extension is published, students install it from its official Chrome Web Store listing and pin it to the toolbar. Click the icon and choose Open sharing controls. Before publication, an administrator can build the project and use Chrome developer mode to load the extension dist folder unpacked. Keep the sharing controls and Chrome open while sharing.

## 3. Join your teacher’s classroom

Enter the exact HTTPS server address and classroom code provided by your teacher. Click Check classroom slash join and review Chrome server access permission. Grant access only to a server you trust. In a code-only classroom, also enter your name and student ID. If your school requires Google sign-in, continue using the Google button instead.

## 4. Use your approved school account

When Google login is required, click Sign in with Google and join. Choose your managed school account. The backend verifies the Google identity and enforces the exact allowed domain list. Other accounts are rejected. Personal Gmail accounts work only if the administrator explicitly allows gmail dot com. The teacher sees your verified name and email. This guide illustrates the step; an actual Google login requires the institution’s configured OAuth client.

## 5. Read the sharing disclosure

Before sharing, read the disclosure in the controls. Your chosen screen or window will be transmitted to your classroom server for the teacher to view. The teacher may enable periodic screenshot recording and optional archive uploads to the teacher’s Google Drive. Anything visible in the selected source can appear in those images. Close private content, then check the acknowledgement.

## 6. Choose a screen or window

Click Start Sharing. Chrome opens its own native permission picker. Select the screen or application window you intend to share, and confirm in Chrome. The illustration here is not the native permission dialog. This product never chooses the source silently. No webcam, microphone or audio capture is requested. On a Mac, Chrome may also need Screen Recording permission in system settings.

## 7. Work in your usual application

You can now switch to VS Code, Jupyter, PyCharm or another application. The selected source continues sharing while available and while Chrome’s authorized capture session remains active. Keep the extension controls open. A minimized or closed application window may stop updating depending on the operating system. Share the full screen if needed. Watch the sharing and recording indicators.

## 8. See progress and offer help

On the teacher dashboard, student cards show the images received from connected extensions. Search by name or student ID and check connection status and the last image timestamp. Click a card to request a larger, higher quality view with more readable code text. Close it or press Escape to return to overview. Up to two distinct students can be focused at once. The dashboard image in this guide is from a browser test with clearly marked synthetic content.

## 9. Record selected moments

Recording is separate from live monitoring and starts off in a new classroom. If appropriate for the class, explain your institution’s policy and enable periodic screenshot recording. The default is one changed screenshot every twenty seconds, with a configurable interval. The system records screenshots, not continuous video. Open Playback to choose a student and review the original timestamps. Optional Google Drive uploads use ZIP batches.

## 10. Stop sharing or end the class

Students can stop immediately using Stop Sharing in the extension controls, the toolbar popup or Chrome’s sharing indicator. Closing the extension controls also stops capture. Teachers end the classroom when the lesson finishes. The old joining code becomes invalid. Short network interruptions can reconnect using the existing authorized stream. After thirty seconds without the server, capture stops and the student must deliberately start sharing again.

## Ready for your first classroom?

Before teaching, test real capture on two devices, including source selection, switching applications, focused viewing, recording playback, Stop Sharing and ending the classroom. Confirm HTTPS works on student devices and approved Google accounts can join if required. Review the student and teacher guides. The demonstration video is ready to share as instructions; it does not replace that real hardware acceptance test.

