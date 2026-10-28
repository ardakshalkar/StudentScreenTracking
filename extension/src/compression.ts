import {qualities, type Mode} from './quality';
export class Compressor {
  private previous?:Uint8ClampedArray;
  private previousMode?:Mode;
  private probe = document.createElement('canvas');
  constructor(private canvas:HTMLCanvasElement) {this.probe.width=96; this.probe.height=54;}
  reset() {this.previous=undefined;}
  async frame(video:HTMLVideoElement, mode:Mode):Promise<Blob|null> {
    if (!video.videoWidth || !video.videoHeight || video.readyState < 2) return null;
    const probe = this.probe.getContext('2d',{willReadFrequently:true})!;
    probe.drawImage(video,0,0,96,54);
    const pixels = probe.getImageData(0,0,96,54).data;
    // Ignore tiny compression noise, but retain small code edits. No frame FIFO.
    let changed = !this.previous || this.previousMode !== mode;
    if (!changed) for(let i=0; i<pixels.length; i+=4) {
      if (Math.abs(pixels[i]-this.previous![i])+Math.abs(pixels[i+1]-this.previous![i+1])+Math.abs(pixels[i+2]-this.previous![i+2]) > 12) {changed=true; break;}
    }
    if (!changed) return null;
    const q = qualities[mode];
    const scale = Math.min(1,q.width/video.videoWidth,1920/video.videoHeight);
    this.canvas.width=Math.round(video.videoWidth*scale);
    this.canvas.height=Math.round(video.videoHeight*scale);
    this.canvas.getContext('2d')!.drawImage(video,0,0,this.canvas.width,this.canvas.height);
    const encode = (quality:number) => new Promise<Blob|null>(resolve => this.canvas.toBlob(resolve,'image/webp',quality));
    let blob = await encode(q.quality);
    if (mode === 'overview' && blob && blob.size > q.maxBytes) blob = await encode(.48);
    if (!blob || blob.size > 950000) return null;
    this.previous = pixels;
    this.previousMode = mode;
    return blob;
  }
}
