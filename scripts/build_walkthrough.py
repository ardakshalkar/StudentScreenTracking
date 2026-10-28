"""Create a narrated instructional MP4 using offline speech + exact UI evidence.

This is a guided walkthrough with illustrations and a real dashboard test
screenshot, not a claim of an actual OS capture permission acceptance test.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import textwrap
import wave

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0,str(Path(__file__).resolve().parent))
from release_assets import font, mark

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'release'/'video'
W,H=1920,1080

SCENES=[
 dict(title='A window into your classroom.',tag='START HERE',kind='network',
      bullets=['Teacher: backend + dashboard','Student: Chrome extension','A classroom server is required'],
      narration='Welcome to Classroom Screen Sharing. Teachers use a website, and students use a Chrome extension. Your teacher or institution must run the classroom backend and dashboard. Installing the extension alone does not create a hosted classroom. This guided demonstration uses sample content and illustrations, not a recording of an accepted native screen capture dialog.'),
 dict(title='1. Prepare the classroom server',tag='TEACHER',kind='network',
      bullets=['Run the backend and dashboard','Use trusted HTTPS on all devices','Share the address + joining code'],
      narration='Teachers first start the backend and dashboard using the project instructions. Give the server a trusted HTTPS address reachable from student laptops. Sign into the teacher website and create a course and session. Share the server address and the eight character classroom code. The same Wi-Fi network can be used, but localhost on a student laptop points to that student laptop, not to the teacher.'),
 dict(title='2. Install and open the extension',tag='STUDENT',kind='install',
      bullets=['Install from the official listing','Pin the extension in Chrome','Open sharing controls'],
      narration='After the extension is published, students install it from its official Chrome Web Store listing and pin it to the toolbar. Click the icon and choose Open sharing controls. Before publication, an administrator can build the project and use Chrome developer mode to load the extension dist folder unpacked. Keep the sharing controls and Chrome open while sharing.'),
 dict(title='3. Join your teacher’s classroom',tag='STUDENT',kind='join',
      bullets=['Enter the exact HTTPS address','Enter the classroom code','Grant access to that server'],
      narration='Enter the exact HTTPS server address and classroom code provided by your teacher. Click Check classroom slash join and review Chrome server access permission. Grant access only to a server you trust. In a code-only classroom, also enter your name and student ID. If your school requires Google sign-in, continue using the Google button instead.'),
 dict(title='4. Use your approved school account',tag='GOOGLE SIGN-IN · OPTIONAL',kind='google',
      bullets=['Choose your managed school account','Only exact allowed domains can join','Personal Gmail must be explicitly allowed'],
      narration='When Google login is required, click Sign in with Google and join. Choose your managed school account. The backend verifies the Google identity and enforces the exact allowed domain list. Other accounts are rejected. Personal Gmail accounts work only if the administrator explicitly allows gmail dot com. The teacher sees your verified name and email. This guide illustrates the step; an actual Google login requires the institution’s configured OAuth client.'),
 dict(title='5. Read the sharing disclosure',tag='YOUR CHOICE',kind='consent',
      bullets=['Your selected source goes to the teacher','Periodic recording may be enabled','Close private content before sharing'],
      narration='Before sharing, read the disclosure in the controls. Your chosen screen or window will be transmitted to your classroom server for the teacher to view. The teacher may enable periodic screenshot recording and optional archive uploads to the teacher’s Google Drive. Anything visible in the selected source can appear in those images. Close private content, then check the acknowledgement.'),
 dict(title='6. Choose a screen or window',tag='CHROME’S NATIVE PICKER',kind='capture',
      bullets=['Click Start Sharing','Choose the intended screen or window','Confirm in Chrome’s own dialog'],
      narration='Click Start Sharing. Chrome opens its own native permission picker. Select the screen or application window you intend to share, and confirm in Chrome. The illustration here is not the native permission dialog. This product never chooses the source silently. No webcam, microphone or audio capture is requested. On a Mac, Chrome may also need Screen Recording permission in system settings.'),
 dict(title='7. Work in your usual application',tag='STUDENT',kind='work',
      bullets=['Switch to VS Code, Jupyter or PyCharm','Keep the extension controls open','Check sharing and recording status'],
      narration='You can now switch to VS Code, Jupyter, PyCharm or another application. The selected source continues sharing while available and while Chrome’s authorized capture session remains active. Keep the extension controls open. A minimized or closed application window may stop updating depending on the operating system. Share the full screen if needed. Watch the sharing and recording indicators.'),
 dict(title='8. See progress and offer help',tag='TEACHER DASHBOARD',kind='dashboard',
      bullets=['Search by name or student ID','Check health and last-frame timestamps','Click a card for focused quality'],
      narration='On the teacher dashboard, student cards show the images received from connected extensions. Search by name or student ID and check connection status and the last image timestamp. Click a card to request a larger, higher quality view with more readable code text. Close it or press Escape to return to overview. Up to two distinct students can be focused at once. The dashboard image in this guide is from a browser test with clearly marked synthetic content.'),
 dict(title='9. Record selected moments',tag='TEACHER · OPTIONAL',kind='record',
      bullets=['Recording starts off','Default: one changed screenshot / 20s','Open Playback to review timestamps'],
      narration='Recording is separate from live monitoring and starts off in a new classroom. If appropriate for the class, explain your institution’s policy and enable periodic screenshot recording. The default is one changed screenshot every twenty seconds, with a configurable interval. The system records screenshots, not continuous video. Open Playback to choose a student and review the original timestamps. Optional Google Drive uploads use ZIP batches.'),
 dict(title='10. Stop sharing or end the class',tag='CLEAR STOP CONTROLS',kind='stop',
      bullets=['Student: Stop Sharing at any time','Teacher: End session when finished','A long outage stops capture'],
      narration='Students can stop immediately using Stop Sharing in the extension controls, the toolbar popup or Chrome’s sharing indicator. Closing the extension controls also stops capture. Teachers end the classroom when the lesson finishes. The old joining code becomes invalid. Short network interruptions can reconnect using the existing authorized stream. After thirty seconds without the server, capture stops and the student must deliberately start sharing again.'),
 dict(title='Ready for your first classroom?',tag='CHECK BEFORE CLASS',kind='finish',
      bullets=['Test real sharing on two devices','Confirm trusted HTTPS and account access','Share the student guide with your class'],
      narration='Before teaching, test real capture on two devices, including source selection, switching applications, focused viewing, recording playback, Stop Sharing and ending the classroom. Confirm HTTPS works on student devices and approved Google accounts can join if required. Review the student and teacher guides. The demonstration video is ready to share as instructions; it does not replace that real hardware acceptance test.'),
]

def wrapped(draw,text,xy,width,size=32,color='#bdd2c8',bold=False,spacing=12):
    x,y=xy;f=font(size,bold)
    words=text.split();line=''
    for word in words:
        candidate=(line+' '+word).strip()
        if draw.textlength(candidate,font=f)>width and line:
            draw.text((x,y),line,font=f,fill=color);y+=size+spacing;line=word
        else:line=candidate
    if line:draw.text((x,y),line,font=f,fill=color);y+=size+spacing
    return y

def base(index,scene):
    image=Image.new('RGB',(W,H),'#102f34');d=ImageDraw.Draw(image)
    d.rectangle((0,0,W,9),fill='#a4d8be')
    image.paste(mark(80),(52,38),mark(80))
    d.text((144,54),'CLASSROOM  /  SCREEN SHARING',font=font(22,True),fill='#d0e3d3')
    d.text((1410,58),'GUIDED WALKTHROUGH',font=font(17),fill='#99b9ac')
    d.text((75,183),scene['tag'],font=font(19,True),fill='#a4d8be')
    wrapped(d,scene['title'],(75,230),750,60,'#f4f6e9',True,8)
    y=475
    for bullet in scene['bullets']:
        d.rounded_rectangle((78,y+11,92,y+25),radius=4,fill='#a4d8be')
        y=wrapped(d,bullet,(115,y),640,31,'#c1d6ca',False,10)+24
    d.line((75,948,1845,948),fill='#35534f',width=2)
    d.text((75,975),'Sample content • illustrations + actual dashboard test image',font=font(18),fill='#97b1a4')
    d.text((1660,974),f'{index+1:02d} / {len(SCENES):02d}',font=font(22,True),fill='#c8ddcc')
    d.rounded_rectangle((75,1042,1845,1050),radius=4,fill='#35534f')
    d.rounded_rectangle((75,1042,int(75+1770*(index+1)/len(SCENES)),1050),radius=4,fill='#a4d8be')
    return image,d

def panel(d,title='INSTRUCTIONAL ILLUSTRATION'):
    d.rounded_rectangle((875,185,1840,880),radius=28,fill='#f2f5ed',outline='#88b69e',width=2)
    d.text((920,221),title,font=font(17,True),fill='#6e8977')

def button(d,box,label,red=False):
    d.rounded_rectangle(box,radius=13,fill='#ecb6a8' if red else '#246a58')
    d.text(((box[0]+box[2])/2,(box[1]+box[3])/2),label,font=font(28,True),fill='#4b2923' if red else '#eef5e8',anchor='mm')

def scene_image(index,scene):
    image,d=base(index,scene);kind=scene['kind']
    if kind=='dashboard':
        source=Image.open(ROOT/'artifacts'/'dashboard-browser-test.png').convert('RGB')
        source=ImageOps.contain(source,(960,710),Image.Resampling.LANCZOS)
        image.paste(source,(875+(960-source.width)//2,185+(710-source.height)//2))
        d.text((920,895),'Actual dashboard screenshot · synthetic test stream',font=font(18),fill='#adc5b6')
    else:
        panel(d)
        if kind=='network':
            for y,label,sub in [(310,'STUDENT LAPTOPS','Chrome extension'),(600,'TEACHER COMPUTER / SERVER','Backend + dashboard + local archives')]:
                d.rounded_rectangle((960,y,1755,y+155),radius=20,fill='#dce9dc',outline='#8ab198',width=2)
                d.text((1000,y+27),label,font=font(25,True),fill='#244e40')
                d.text((1000,y+76),sub,font=font(25),fill='#4d6c59')
            d.line((1350,480,1350,570),fill='#43816a',width=7)
            d.polygon([(1335,555),(1365,555),(1350,579)],fill='#43816a')
            d.text((1390,510),'HTTPS / WSS',font=font(22,True),fill='#43816a')
        elif kind=='join':
            for y,label,value in [(310,'Classroom server URL','https://your-school-server.example'),(465,'Classroom code','ABCDEFGH')]:
                d.text((950,y),label,font=font(23),fill='#587460')
                d.rounded_rectangle((950,y+47,1760,y+118),radius=10,fill='white',outline='#b3c9b4',width=2)
                d.text((977,y+62),value,font=font(27),fill='#244f40')
            button(d,(950,678,1760,758),'Check classroom / join')
            d.text((950,800),'Use the address and code from your teacher.',font=font(22),fill='#6d8471')
        elif kind=='google':
            d.text((950,312),'Approved school account',font=font(34,True),fill='#264f40')
            d.text((950,394),'student@school.edu',font=font(31),fill='#507760')
            button(d,(950,510,1760,605),'Sign in with Google & join')
            wrapped(d,'Illustration only. Your school configures the actual allowed domains and Google client.',(950,670),780,26,'#6a806b')
        elif kind=='consent':
            d.text((950,310),'Before you share',font=font(40,True),fill='#254f40')
            wrapped(d,'Your teacher can view the selected source. The classroom may save periodic screenshots.',(950,400),770,32,'#4f6f5b')
            d.rounded_rectangle((950,600,994,644),radius=7,outline='#397454',width=3)
            d.line([(958,621),(972,636),(989,609)],fill='#397454',width=5)
            wrapped(d,'I understand who can view my screen and that screenshots may be recorded.',(1025,593),700,27,'#4f6f5b')
        elif kind=='capture':
            d.text((950,310),'Use Chrome’s real picker',font=font(36,True),fill='#234e40')
            for x,label in [(960,'Entire screen'),(1370,'Application window')]:
                d.rounded_rectangle((x,437,x+355,651),radius=14,fill='#dbe7dc',outline='#73977e',width=3)
                d.rounded_rectangle((x+38,470,x+315,587),radius=9,outline='#4c785d',width=4)
                d.text((x+177,624),label,font=font(23,True),fill='#3a674d',anchor='mm')
            wrapped(d,'Instructional diagram — not a screenshot of Chrome’s native permission dialog.',(950,730),780,24,'#788871')
        elif kind=='install':
            d.text((950,315),'Classroom Screen Sharing',font=font(38,True),fill='#264f40')
            image.paste(mark(150),(1250,410),mark(150))
            button(d,(970,640,1740,720),'Open sharing controls')
            d.text((970,784),'Official store install becomes available after approval.',font=font(21),fill='#667f69')
        elif kind=='work':
            d.rounded_rectangle((950,300,1765,670),radius=14,fill='#1a3039')
            for i,line in enumerate(['def average(values):','    total = sum(values)','    return total / len(values)','','scores = [84, 92, 88]','print(average(scores))']):
                d.text((985,335+i*43),line,font=font(27),fill='#b9d9bf')
            d.rounded_rectangle((950,715,1765,810),radius=12,fill='#dce9db')
            d.text((985,744),'● SHARING  /  Recording status visible',font=font(27,True),fill='#386c4b')
        elif kind=='record':
            d.text((950,315),'Periodic screenshots',font=font(38,True),fill='#264f40')
            d.text((950,408),'20 seconds',font=font(70,True),fill='#4c7c55')
            d.text((955,510),'Default interval · changed screens only',font=font(26),fill='#718468')
            for i in range(5):
                x=960+i*160;d.rounded_rectangle((x,600,x+130,686),radius=9,fill='#245346')
                d.text((x+65,729),f'00:{i*20:02d}' if i<3 else f'01:{(i-3)*20:02d}',font=font(20),fill='#6c856c',anchor='mm')
            button(d,(1110,780,1600,846),'Open Playback')
        elif kind=='stop':
            d.text((950,315),'You can stop at any time.',font=font(35,True),fill='#264f40')
            button(d,(970,450,1740,552),'Stop Sharing',True)
            button(d,(970,620,1740,722),'Teacher: End session')
            d.text((970,795),'Closing sharing controls also ends capture.',font=font(24),fill='#6f846c')
        else:
            for i,line in enumerate(['Trusted HTTPS on both devices','Approved account + active code','Real Chrome source selection','Working Stop + session-end controls']):
                y=330+i*115;d.ellipse((955,y+8,986,y+39),fill='#6b9c72');d.text((1015,y),line,font=font(27,True),fill='#426747')
    return image

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    for index,scene in enumerate(SCENES):scene_image(index,scene).save(OUT/f'scene-{index+1:02d}.png')
    (OUT/'scenes.json').write_text(json.dumps(SCENES,indent=2,ensure_ascii=False),encoding='utf-8')
    transcript='# Classroom Screen Sharing · narrated walkthrough\n\nGuided illustrations and a real dashboard test screenshot; sample content. Not a native capture acceptance test.\n\n'
    for scene in SCENES:transcript+='## '+scene['title']+'\n\n'+scene['narration']+'\n\n'
    (OUT/'TRANSCRIPT.md').write_text(transcript,encoding='utf-8')
    print('Prepared 12 full-HD instructional scenes and narration script.')

def timestamp(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def encode():
    clips=[];subtitles=[];offset=0;counter=1;chapters=[]
    for index,scene in enumerate(SCENES):
        stem=f'scene-{index+1:02d}';audio=OUT/(stem+'.wav')
        with wave.open(str(audio)) as wav:spoken=wav.getnframes()/wav.getframerate()
        duration=spoken+1.5
        clip=OUT/(stem+'.mp4')
        command=['ffmpeg','-y','-loglevel','error','-loop','1','-i',str(OUT/(stem+'.png')),'-i',str(audio),
            '-c:v','libx264','-preset','fast','-tune','stillimage','-crf','20','-pix_fmt','yuv420p','-r','24',
            '-c:a','aac','-b:a','128k','-af','apad','-t',str(duration),'-movflags','+faststart',str(clip)]
        subprocess.run(command,check=True)
        clips.append("file '"+clip.name+"'")
        chapters.append({'start_seconds':round(offset,2),'title':scene['title'],'duration_seconds':round(duration,2)})
        words=scene['narration'].split();chunks=[' '.join(words[i:i+16]) for i in range(0,len(words),16)]
        total=sum(len(chunk.split()) for chunk in chunks);cursor=offset
        for chunk in chunks:
            length=spoken*len(chunk.split())/total
            subtitles.append(f'{counter}\n{timestamp(cursor)} --> {timestamp(cursor+length)}\n'+textwrap.fill(chunk,72)+'\n')
            cursor+=length;counter+=1
        offset+=duration
        print(f'Encoded scene {index+1}/{len(SCENES)} ({duration:.1f}s)',flush=True)
    concat=OUT/'clips.txt';concat.write_text('\n'.join(clips)+'\n')
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(OUT/'classroom-walkthrough.mp4')],check=True)
    (OUT/'classroom-walkthrough.srt').write_text('\n'.join(subtitles),encoding='utf-8')
    (OUT/'chapters.json').write_text(json.dumps(chapters,indent=2))
    (OUT/'video-report.json').write_text(json.dumps({'duration_seconds':round(offset,2),'resolution':[W,H],'fps':24,'narration':'Offline Windows Microsoft Zira speech synthesis','scene_count':len(SCENES),
        'disclosure':'Guided illustrations + actual dashboard test screenshot; sample classroom content; not native capture verification.'},indent=2))
    print(f'Created narrated MP4: {offset:.1f}s',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('step',choices=['prepare','encode']);args=parser.parse_args()
    prepare() if args.step=='prepare' else encode()
