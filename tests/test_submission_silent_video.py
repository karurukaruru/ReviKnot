import hashlib
import json

import pytest

from scripts.submission_check import check_video


def silent_video(tmp_path):
    video=tmp_path/'demo.mp4'
    video.write_bytes(b'test bytes bound to a separately reviewed video record')
    record={'sha256':hashlib.sha256(video.read_bytes()).hexdigest(), 'duration_seconds':96,
            'visual_review':'PASS','presentation':'music-and-on-screen-english',
            'english_on_screen_review':'PASS','platform_model_on_screen_review':'PASS'}
    (tmp_path/'video.json').write_text(json.dumps(record),encoding='utf-8')
    item={'file':'demo.mp4','manifest':'video.json','english_reviewed':True,
          'competition_runtime_shown':True,'spoken_platform_attribution':False,
          'visual_platform_attribution':True}
    return item,record


def test_reviewed_silent_english_video_is_accepted(tmp_path):
    item,_=silent_video(tmp_path)
    assert 'Hash-checked' in check_video(tmp_path,item)


@pytest.mark.parametrize('field',['english_on_screen_review','platform_model_on_screen_review','presentation'])
def test_no_voice_cannot_bypass_attribution_and_language_review(tmp_path,field):
    item,record=silent_video(tmp_path)
    record[field]='PENDING'
    (tmp_path/'video.json').write_text(json.dumps(record),encoding='utf-8')
    with pytest.raises(ValueError,match='attribution'):
        check_video(tmp_path,item)


def test_silent_video_still_requires_actual_runtime_footage_review(tmp_path):
    item,_=silent_video(tmp_path)
    item['competition_runtime_shown']=False
    with pytest.raises(ValueError,match='actual Nebius'):
        check_video(tmp_path,item)
