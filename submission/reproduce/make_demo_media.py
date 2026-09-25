#!/usr/bin/env python3
"""Rotate the recorded VGA display for publication; create MP4 and animated GIF."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    ap.add_argument('--ffmpeg', type=Path)
    ap.add_argument('--ffprobe', type=Path)
    a = ap.parse_args()
    local = ROOT/'build/media_tools/root/usr'
    ffmpeg = a.ffmpeg or shutil.which('ffmpeg') or local/'bin/ffmpeg'
    ffprobe = a.ffprobe or shutil.which('ffprobe') or local/'bin/ffprobe'
    env = dict(os.environ)
    if Path(ffmpeg).is_relative_to(local):
        lib = local/'lib/aarch64-linux-gnu'
        env['LD_LIBRARY_PATH'] = ':'.join(map(str, [lib,lib/'blas',lib/'lapack']))
    def run(args, capture=False):
        return subprocess.run(list(map(str,args)), env=env, check=True, capture_output=capture, text=capture)
    source = a.source.resolve(); out = ROOT/'docs/images'; out.mkdir(exist_ok=True)
    probe = json.loads(run([ffprobe,'-v','error','-show_format','-show_streams','-of','json',source],True).stdout)
    stream = next(s for s in probe['streams'] if s['codec_type']=='video')
    video = out/'fpga-vga-animation-20260925.mp4'; gif = out/'fpga-vga-animation-20260925.gif'
    video_filter = 'transpose=cclock,scale=960:-2,setsar=1'
    run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',source,'-map','0:v:0','-an','-sn','-dn',
         '-vf',video_filter,'-c:v','libx264','-crf','23','-preset','medium','-pix_fmt','yuv420p',
         '-map_metadata','-1','-metadata:s:v:0','rotate=0','-movflags','+faststart',video])
    gif_filter = 'fps=15,scale=640:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3'
    run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',video,'-filter_complex',gif_filter,'-loop','0',gif])
    output = json.loads(run([ffprobe,'-v','error','-show_format','-show_streams','-of','json',video],True).stdout)
    assert len(output['streams'])==1 and output['streams'][0]['codec_type']=='video'
    assert not any('location' in k for k in output['format'].get('tags',{}))
    assert output['streams'][0]['width']==960 and output['streams'][0]['height']==540
    assert all(d.get('rotation',0)==0 for d in output['streams'][0].get('side_data_list',[]))
    report = {'source_name':source.name,'source_sha256':sha(source),'source_duration_seconds':float(probe['format']['duration']),
              'role':'FPGA monitor recording; not an ASIC silicon measurement or simulator output',
              'rotation':'90 degrees counterclockwise after input display-matrix orientation',
              'video_filter':video_filter,'gif_filter':gif_filter,'video_pixels':[960,540],'gif_pixels':[640,360],
              'audio_in_published_video':False,'ffmpeg_version':run([ffmpeg,'-version'],True).stdout.splitlines()[0],
              'files':{p.name:sha(p) for p in [video,gif]},'script_sha256':sha(Path(__file__))}
    (out/'fpga-vga-animation-20260925.json').write_text(json.dumps(report,indent=2)+'\n')
    print(video);print(gif)


if __name__=='__main__':main()
