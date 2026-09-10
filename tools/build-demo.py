#!/usr/bin/env python3
"""Apply camera framing and captions to one continuous native desktop capture.

Requires ffmpeg. All desktop surfaces are transformed together; no UI overlays,
repositioned menus, image cards, or composite desktop elements are introduced.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
# Time/zoom keyframes. Camera stays aligned to the desktop's top-right corner.
KEYS = [(0,1),(1,1),(3,2.25),(4.7,2.25),(6.7,1),(8,1),
        (9.2,1.5),(10.1,1.5),(11.5,1.22),(22.5,1.22),
        (24.7,1.8),(27.7,1.8),(30,1),(32,1)]


def zoom_expression():
    result = str(KEYS[-1][1])
    for (a,za),(b,zb) in reversed(list(zip(KEYS,KEYS[1:]))):
        u = f'((on/30-{a})/{b-a})'
        value = str(za) if za == zb else f'({za}+({zb-za})*{u}*{u}*(3-2*{u}))'
        result = f'if(lt(on/30,{b}),{value},{result})'
    return result


def main():
    with tempfile.TemporaryDirectory() as tmp:
        caption_files = []
        for i, text in enumerate(['Light to dark. One click.',
                                 'Right-click to choose your favorites.',
                                 'Preview. Pick. Remember.',
                                 'Your favorites, one click apart.']):
            p = Path(tmp)/f'caption-{i}.txt'; p.write_text(text); caption_files.append(p)
        z = zoom_expression()
        filters = [f"fps=30,zoompan=z='{z}':x='iw-iw/zoom':y=0:d=1:s=1280x800:fps=30",
                   'drawbox=x=0:y=690:w=iw:h=110:color=0x0c1726@0.86:t=fill',
                   "drawtext=font='DejaVu Sans':text='ThemerToggle':fontsize=15:fontcolor=0xaec9d3:x=36:y=711"]
        for i,(start,end) in enumerate([(0,8),(8,16),(16,25),(25,40)]):
            filters.append(f"drawtext=font='DejaVu Sans':textfile='{caption_files[i]}':fontsize=25:fontcolor=white:x=36:y=741:enable='gte(t,{start})*lt(t,{end})'")
        out = Path(tmp)/'demo.mp4'
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(ROOT/'assets/source/demo-native.mp4'),
                        '-vf',','.join(filters),'-c:v','libx264','-preset','medium','-crf','19',
                        '-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
        gif = Path(tmp)/'demo.gif'
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(out),'-filter_complex',
                        '[0:v]fps=10,scale=640:-1:flags=lanczos,split[a][b];'
                        '[a]palettegen=max_colors=128:stats_mode=diff[p];'
                        '[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle',str(gif)],check=True)
        (ROOT/'assets/demo.mp4').write_bytes(out.read_bytes())
        (ROOT/'assets/demo.gif').write_bytes(gif.read_bytes())


if __name__ == '__main__':
    main()
