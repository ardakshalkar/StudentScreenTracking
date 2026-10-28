// The desktop picker and getUserMedia run in the SAME persistent extension page.
// Nothing requests a camera or audio track, nor moves capture into a service worker.
let pendingPicker:number|undefined;
export function cancelPicker() {
  if(pendingPicker!==undefined) chrome.desktopCapture.cancelChooseDesktopMedia(pendingPicker);
  pendingPicker=undefined;
}
export function chooseScreen():Promise<MediaStream> {
  return new Promise((resolve,reject) => {
    pendingPicker=chrome.desktopCapture.chooseDesktopMedia(['screen','window'], async id => {
      pendingPicker=undefined;
      if (chrome.runtime.lastError) return reject(Error(chrome.runtime.lastError.message));
      if (!id) return reject(Error('Screen selection cancelled. Nothing is being shared.'));
      try {
        const stream = await navigator.mediaDevices.getUserMedia({audio:false,video:{mandatory:{
          chromeMediaSource:'desktop',chromeMediaSourceId:id,maxWidth:1920,maxHeight:1920,maxFrameRate:5,
        }} as MediaTrackConstraints});
        resolve(stream);
      } catch (error) { reject(error); }
    });
  });
}
