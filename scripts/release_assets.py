"""Deterministic vector-style branding and release artwork; no student data."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'release'/'store-assets'
FONT=Path('C:/Windows/Fonts')

def font(size,bold=False):
    candidates=[FONT/('segoeuib.ttf' if bold else 'segoeui.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for candidate in candidates:
        if candidate.exists():return ImageFont.truetype(str(candidate),size)
    return ImageFont.load_default(size=size)

def mark(size):
    image=Image.new('RGBA',(512,512))
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((64,64,448,448),radius=86,fill='#133b3c',outline='#92ceb6',width=8)
    for x,y in [(134,145),(270,145),(134,265),(270,265)]:
        draw.rounded_rectangle((x,y,x+108,y+86),radius=13,fill='#a9dac1')
        draw.line((x+22,y+28,x+80,y+28),fill='#235c51',width=7)
        draw.line((x+22,y+47,x+64,y+47),fill='#235c51',width=6)
    draw.ellipse((368,365,402,399),fill='#e7f2b0')
    return image.resize((size,size),Image.Resampling.LANCZOS)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    icons=ROOT/'extension'/'icons';icons.mkdir(exist_ok=True)
    for size in (16,32,48,128):mark(size).save(icons/f'icon-{size}.png')
    mark(128).save(OUT/'store-icon-128.png')
    mark(512).save(OUT/'brand-mark-512.png')
    # A native, editable source for the simple grid/monitor mark.
    (icons/'icon.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect x="64" y="64" width="384" height="384" rx="86" fill="#133b3c" stroke="#92ceb6" stroke-width="8"/><g fill="#a9dac1"><rect x="134" y="145" width="108" height="86" rx="13"/><rect x="270" y="145" width="108" height="86" rx="13"/><rect x="134" y="265" width="108" height="86" rx="13"/><rect x="270" y="265" width="108" height="86" rx="13"/></g><circle cx="385" cy="382" r="17" fill="#e7f2b0"/></svg>''')
    image=Image.new('RGB',(440,280),'#14383c');draw=ImageDraw.Draw(image)
    image.paste(mark(90),(23,17),mark(90))
    draw.text((30,122),'Classroom',font=font(37,True),fill='#f0f4e9')
    draw.text((30,167),'Screen Sharing',font=font(27),fill='#b1ddc2')
    draw.text((32,228),'Your screen. Your choice.',font=font(16),fill='#ccdad0')
    image.save(OUT/'promo-440x280.png')
    image=Image.new('RGB',(1400,560),'#14383c');draw=ImageDraw.Draw(image)
    image.paste(mark(300),(100,125),mark(300))
    draw.text((465,125),'A window into',font=font(66,True),fill='#f1f5e9')
    draw.text((465,210),'your classroom.',font=font(66,True),fill='#b1ddc2')
    draw.text((470,345),'Students choose what to share.',font=font(29),fill='#dde8dd')
    draw.text((470,398),'Companion extension · classroom server required',font=font(20),fill='#9ebbb2')
    image.save(OUT/'marquee-1400x560.png')
    screenshot=ROOT/'artifacts'/'dashboard-browser-test.png'
    if screenshot.exists():
        image=Image.new('RGB',(1280,800),'#f4f6ef');draw=ImageDraw.Draw(image)
        draw.text((45,26),'Your classroom, live.',font=font(36,True),fill='#193f3b')
        draw.text((47,78),'Teacher dashboard · sample classroom content',font=font(17),fill='#567469')
        screen=Image.open(screenshot).convert('RGB')
        screen=ImageOps.contain(screen,(1190,610),Image.Resampling.LANCZOS)
        image.paste(screen,((1280-screen.width)//2,125))
        draw.text((47,758),'Requires a teacher/institution-hosted server. Sample images shown.',font=font(15),fill='#5a7567')
        image.save(OUT/'screenshot-01-dashboard-1280x800.png')
    print('Created extension icons and Chrome Web Store artwork.')

if __name__=='__main__':main()
