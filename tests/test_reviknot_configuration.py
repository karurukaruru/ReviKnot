"""Operator-configured limits and product aliases, using temporary ledgers only."""
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

from patchcourt import providers
from patchcourt.budget import RequestBudget
from patchcourt.cli import main
from patchcourt.evidence import read_json
from patchcourt.live_workflow import run_live_workflow
from scripts import run_release_experiments as release
from tests.test_patchcourt_live_workflow import PLAN, replies, response


def test_explicit_operator_adjustment_keeps_prior_reservations_and_requires_a_reason(tmp_path):
    path=tmp_path/'budget.json'
    budget=RequestBudget(path)
    budget.reserve('deepseek',{'max_tokens':100})
    previous=read_json(path)['reservations']
    with patch('sys.stderr',new_callable=io.StringIO):
        assert main(['budget',str(path),'--model-calls','36'])==2
    assert read_json(path)['limits']['model_calls']==30
    with patch('sys.stdout',new_callable=io.StringIO) as output:
        assert main(['budget',str(path),'--model-calls','36','--reason','Synthetic explicit six-request authorization'])==0
    saved=read_json(path)
    assert saved['limits']=={'model_calls':36,'searches':10,'discovery_calls':5}
    assert saved['reservations']==previous
    assert len(saved['limit_adjustments'])==1
    assert json.loads(output.getvalue())['provider_requests']==0
    with pytest.raises(ValueError,match='identity'):
        RequestBudget(path)


def release_args(tmp_path,budget,extra=()):
    return ['live','--provider','nebius','--model','nvidia/Nemotron-synthetic',
            '--env-file',str(tmp_path/'not-read.env'),'--budget',str(budget),
            '--output',str(tmp_path/'experiment'),*extra]


def test_release_runner_reuses_exact_saved_limits_without_resetting_or_reading_credentials(tmp_path,monkeypatch):
    path=tmp_path/'budget.json'
    budget=RequestBudget(path)
    budget.reserve('deepseek',{'max_tokens':100})
    budget.adjust_limits(model_calls=36,reason='Synthetic authorized extension')
    before=path.read_bytes()
    credentials=Mock()
    execute=Mock(return_value={'status':'PASS'})
    monkeypatch.setattr(release,'load_local_credentials',credentials)
    monkeypatch.setattr(release,'execute',execute)
    with patch('sys.stdout',new_callable=io.StringIO) as output:
        assert release.main(release_args(tmp_path,path))==0
    assert json.loads(output.getvalue())['budget_limits']['model_calls']==36
    assert path.read_bytes()==before
    credentials.assert_called_once()
    execute.assert_called_once()


def test_release_explicit_mismatch_is_not_an_implicit_adjustment_or_credential_load(tmp_path,monkeypatch):
    path=tmp_path/'budget.json'
    RequestBudget(path)
    before=path.read_bytes()
    credentials=Mock(); execute=Mock()
    monkeypatch.setattr(release,'load_local_credentials',credentials)
    monkeypatch.setattr(release,'execute',execute)
    with patch('sys.stdout',new_callable=io.StringIO):
        assert release.main(release_args(tmp_path,path,['--model-calls','36']))==2
    assert path.read_bytes()==before
    credentials.assert_not_called();execute.assert_not_called()


def test_release_new_ledger_accepts_explicit_large_bounded_limits(tmp_path,monkeypatch):
    path=tmp_path/'budget.json'
    monkeypatch.setattr(release,'load_local_credentials',Mock())
    monkeypatch.setattr(release,'execute',Mock(return_value={'status':'PASS'}))
    with patch('sys.stdout',new_callable=io.StringIO):
        assert release.main(release_args(tmp_path,path,['--model-calls','200','--searches','20']))==0
    assert read_json(path)['limits']=={'model_calls':200,'searches':20,'discovery_calls':5}


def test_cli_custom_workflow_limits_are_forwarded_to_live_and_workbench(tmp_path):
    flags=['--max-model-requests','200','--max-tool-turns','12','--max-repair-attempts','4',
           '--max-output-tokens','8192','--token-reservation-limit','2000000']
    expected={'max_model_requests':200,'max_tool_turns':12,'max_repair_attempts':4,
              'max_output_tokens':8192,'token_reservation_limit':2000000}
    with patch('patchcourt.live_workflow.run_live_workflow',return_value={'status':'BLOCKED','total_reported_tokens':None}) as run,patch('sys.stdout',new_callable=io.StringIO):
        assert main(['live','--output',str(tmp_path/'run'),*flags])==2
    assert all(run.call_args.kwargs[key]==value for key,value in expected.items())
    with patch('patchcourt.live_demo.serve_live_demo') as serve:
        assert main(['live-demo','--max-runs','7',*flags])==0
    assert serve.call_args.kwargs['max_runs']==7
    assert all(serve.call_args.kwargs[key]==value for key,value in expected.items())


def test_real_workflow_report_and_payload_use_custom_limits(tmp_path,monkeypatch):
    queue=iter(replies());sent=[]
    def transport(provider,payload):
        sent.append(deepcopy(payload));return next(queue)
    monkeypatch.setattr(providers,'request',transport)
    report=run_live_workflow(tmp_path/'run',max_model_requests=200,max_tool_turns=12,
        max_repair_attempts=4,token_reservation_limit=2000000,max_output_tokens=8192)
    assert report['status']=='PASS'
    assert report['limits']['max_model_requests']==200
    assert report['limits']['max_tool_turns']==12
    assert report['limits']['max_proposal_attempts']==report['limits']['max_repair_attempts']==4
    assert report['limits']['input_bytes_plus_output_budget']==2000000
    assert report['limits']['max_output_tokens_per_request']==8192
    assert [payload['max_tokens'] for payload in sent]==[8192]*3


def test_fourth_model_proposal_is_possible_only_when_explicitly_configured(tmp_path,monkeypatch):
    bad=response({'content':json.dumps({**PLAN,'preserve_legacy':False})})
    queue=iter([deepcopy(bad) for _ in range(3)]+replies())
    transport=Mock(side_effect=lambda *args,**kwargs:next(queue))
    monkeypatch.setattr(providers,'request',transport)
    report=run_live_workflow(tmp_path/'run',max_repair_attempts=4)
    assert report['status']=='PASS' and len(report['repair_attempts'])==4
    assert [row['verification']['status'] for row in report['repair_attempts']]==['REJECTED']*3+['VERIFIED']
    assert transport.call_count==6


def test_tool_conversation_can_complete_after_the_old_four_turn_ceiling(tmp_path,monkeypatch):
    values=replies()
    calls=values[1]['response']['choices'][0]['message']['tool_calls']
    rounds=[]
    for index in range(4):
        call=deepcopy(calls[0]);call['id']='inventory-'+str(index)
        rounds.append(response({'content':None,'tool_calls':[call]}))
    price=deepcopy(calls[1]);price['id']='price-final'
    rounds.append(response({'content':None,'tool_calls':[price]}))
    transport=Mock(side_effect=[values[0],*rounds,values[-1]])
    monkeypatch.setattr(providers,'request',transport)
    report=run_live_workflow(tmp_path/'run',max_tool_turns=8)
    assert report['status']=='PASS' and len(report['task']['tools'])==5
    assert transport.call_count==7


@pytest.mark.parametrize('limits',[
    {'max_model_requests':1},{'max_tool_turns':1},{'token_reservation_limit':1},
])
def test_explicit_operational_ceiling_stops_with_uncertainty_not_a_fake_regression(tmp_path,monkeypatch,limits):
    transport=Mock(side_effect=replies())
    monkeypatch.setattr(providers,'request',transport)
    report=run_live_workflow(tmp_path/'run',**limits)
    assert report['status']=='INCONCLUSIVE'
    assert transport.call_count<3


@pytest.mark.parametrize('limits',[
    {'max_model_requests':0},{'max_model_requests':10001},{'max_tool_turns':True},
    {'max_repair_attempts':-1},{'max_output_tokens':65537},
])
def test_invalid_configuration_fails_before_any_output_or_provider_dispatch(tmp_path,monkeypatch,limits):
    transport=Mock();monkeypatch.setattr(providers,'request',transport)
    with pytest.raises(ValueError):
        run_live_workflow(tmp_path/'run',**limits)
    transport.assert_not_called()
    assert not (tmp_path/'run').exists()


def test_primary_and_compatibility_module_commands_share_the_branded_cli():
    from reviknot.cli import main as branded
    assert branded is main
    versions=[]
    for module in ('reviknot','patchcourt'):
        result=subprocess.run([sys.executable,'-m',module,'--version'],capture_output=True,text=True,timeout=10)
        assert result.returncode==0 and result.stdout.startswith('ReviKnot ')
        versions.append(result.stdout)
    assert versions[0]==versions[1]
    help_result=subprocess.run([sys.executable,'-m','reviknot','live-demo','--help'],capture_output=True,text=True,timeout=10)
    assert help_result.returncode==0
    assert all(flag in help_result.stdout for flag in ('--max-model-requests','--max-tool-turns','--max-repair-attempts','--max-runs','--budget'))
