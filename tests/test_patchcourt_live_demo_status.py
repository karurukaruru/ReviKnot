"""Local handler and actual viewer-script state transitions, with no providers."""
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

import pytest

from patchcourt.live_demo import serve_live_demo
from patchcourt.live_workflow import WorkflowUnavailable
from tests.test_patchcourt_live_demo_reuse import Connection, ImmediateThread


def exercise_demo(tmp_path, outcomes, thread=ImmediateThread,**configuration):
    snapshots, posts = [], []
    class FakeServer:
        def __init__(self,address,handler):
            self.handler=handler
            self.server_address=address
            self.server_name,self.server_port=address
        def call(self,method,path,session=''):
            headers=[f'{method} {path} HTTP/1.0','Host: 127.0.0.1:8780']
            if method=='POST':
                headers+=['Origin: http://127.0.0.1:8780','Content-Type: application/json',
                          'Content-Length: 2','X-PatchCourt-Session: '+session]
            connection=Connection(('\r\n'.join(headers)+'\r\n\r\n').encode()+(b'{}' if method=='POST' else b''))
            self.handler(connection,('127.0.0.1',60000),self)
            head,body=bytes(connection.output).split(b'\r\n\r\n',1)
            return int(head.split(b' ')[1]),json.loads(body)
        def serve_forever(self):
            session=self.call('GET','/session')[1]['session']
            for _ in outcomes:
                posts.append(self.call('POST','/run',session))
                snapshots.append(deepcopy(self.call('GET','/state')[1]))
                # A poll must read the terminal state without initiating work.
                assert self.call('GET','/state')[1]==snapshots[-1]
            if len(outcomes)==configuration.get('max_runs',3):
                assert self.call('POST','/run',session)[0]==429
        def server_close(self): pass
    with patch('patchcourt.live_demo.ThreadingHTTPServer',FakeServer),patch(
            'patchcourt.live_demo.threading.Thread',thread),patch(
            'patchcourt.live_demo.run_live_workflow',side_effect=outcomes) as workflow,patch(
            'sys.stdout',new_callable=io.StringIO):
        serve_live_demo(tmp_path/'runs',**configuration)
    return snapshots,posts,workflow.call_count


def test_demo_preserves_terminal_status_clears_old_errors_and_never_retries(tmp_path):
    states,posts,calls=exercise_demo(tmp_path,[OSError('synthetic storage failure'),
        {'status':'BLOCKED','reason':'synthetic unavailable credential'},
        {'status':'PASS'}])
    assert [state['status'] for state in states]==['INCONCLUSIVE','BLOCKED','PASS']
    assert states[0]['report'] is None and 'synthetic storage failure' in states[0]['error']
    assert all('error' not in state for state in states[1:])
    assert [state['runs'] for state in states]==[1,2,3]
    assert all(post[0]==202 for post in posts) and calls==3


@pytest.mark.parametrize('outcome,expected',[
    (WorkflowUnavailable('synthetic blocked prerequisite','BLOCKED'),'BLOCKED'),
    ({'status':'INCONCLUSIVE','reason':'synthetic incomplete transport'},'INCONCLUSIVE'),
    ({'status':'RUNNING'},'INCONCLUSIVE'),
    ({'status':'FAIL','reason':'synthetic executed rejection'},'FAIL'),
])
def test_demo_reports_only_supported_terminal_states(tmp_path,outcome,expected):
    states,posts,calls=exercise_demo(tmp_path,[outcome])
    assert states[0]['status']==expected and posts[0][0]==202 and calls==1


def test_thread_start_failure_does_not_leave_an_active_or_retrying_run(tmp_path):
    class FailedThread(ImmediateThread):
        def start(self): raise RuntimeError('synthetic thread start failure')
    states,posts,calls=exercise_demo(tmp_path,[{'status':'PASS'}],thread=FailedThread)
    assert states[0]['status']=='INCONCLUSIVE' and states[0]['runs']==1
    assert 'synthetic thread start failure' in states[0]['error']
    assert posts[0][0]==503 and calls==0


def test_workbench_exposes_and_enforces_explicit_startup_limits(tmp_path):
    states,posts,calls=exercise_demo(tmp_path,[{'status':'BLOCKED'},{'status':'BLOCKED'}],
        max_runs=2,max_model_requests=200,max_tool_turns=12,max_repair_attempts=4,max_output_tokens=8192)
    assert calls==2 and len(posts)==2
    assert states[-1]['limits']['max_runs']==2
    assert states[-1]['limits']['max_model_requests']==200
    assert states[-1]['limits']['max_tool_turns']==12
    assert states[-1]['limits']['max_output_tokens']==8192


def test_actual_viewer_script_handles_inconclusive_without_reposting():
    executable=shutil.which('node')
    if executable is None:
        pytest.skip('Node is optional; needed to execute the actual inline viewer script')
    script=Path(__file__).with_name('live_status_script_check.cjs')
    result=subprocess.run([executable,str(script)],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
