"""Register an actually reviewed local movie without publishing anything."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    folder=args.directory.resolve()
    qa=json.loads((folder/'验收_QA.json').read_text(encoding='utf-8'))
    assert qa['status']=='PASS' and qa['visual_review']=='PASS'
    silent=qa.get('version')=='0.6.0'
    video=folder/('ReviKnot-96s-Demo.mp4' if silent else 'ReviKnot-96s-Preview.mp4')
    checksum=hashlib.sha256(video.read_bytes()).hexdigest()
    assert checksum==qa['files'][video.name]['sha256']
    assert qa['duration_seconds']==96 and qa['subtitles']==(20 if silent else 18)
    viewer=json.loads((folder/'播放器验收_Viewer-QA.json').read_text(encoding='utf-8'))
    assert viewer['status']=='PASS' and not viewer['browser_errors']
    assert viewer['viewer_sha256']==hashlib.sha256((folder/'看片_Review.html').read_bytes()).hexdigest()
    if silent:
        assert qa['narration'] is False and viewer['narration'] is False
        assert viewer['movie_sha256']==checksum
        assert qa['captions_sha256']==viewer['captions_sha256']==hashlib.sha256((folder/'Onscreen-Captions.json').read_bytes()).hexdigest()
        assert qa['source_report_sha256']==hashlib.sha256((ROOT/'evidence/nebius-060/live-01/report.json').read_bytes()).hexdigest()
        assert qa['english_on_screen_review']==qa['platform_model_on_screen_review']=='PASS'
    dest=ROOT/('evidence/video-060' if silent else 'evidence/video-053')
    dest.mkdir(parents=True,exist_ok=True)
    for name in (video.name,'验收_QA.json','播放器验收_Viewer-QA.json','ReviKnot-96s.en.srt','ReviKnot-96s.zh-CN.srt'):
        shutil.copyfile(folder/name,dest/name)
    if silent:
        shutil.copyfile(folder/'Onscreen-Captions.json',dest/'Onscreen-Captions.json')
    manifest={'sha256':checksum,'duration_seconds':96,'visual_review':'PASS','scope':'Local master decoded and inspected; native NVIDIA report and local spoken platform attribution reviewed. Not a public upload.'}
    if silent:
        manifest.update(presentation='music-and-on-screen-english',english_on_screen_review='PASS',platform_model_on_screen_review='PASS',
            scope='Local no-voice English on-screen presentation reviewed against actual NVIDIA and MCP records; not a public upload.')
    (dest/'video-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    path=ROOT/'submission-manifest.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    relative=dest.relative_to(ROOT).as_posix()
    data['video']={'file':relative+'/'+video.name,'manifest':relative+'/video-manifest.json','english_reviewed':True,'competition_runtime_shown':True,'spoken_platform_attribution':not silent}
    if silent:
        data['video']['visual_platform_attribution']=True
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'REGISTERED','video_sha256':checksum,'published':False}))

if __name__=='__main__':
    main()
