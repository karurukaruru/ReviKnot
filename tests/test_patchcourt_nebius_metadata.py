"""Offline Nebius envelope compatibility; no credentials or provider requests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from patchcourt import providers
from patchcourt.evidence import read_json
from patchcourt.live_workflow import run_live_workflow
from patchcourt.repair_plan import validate_plan, verify_plan
from tests.test_patchcourt_live_workflow import PLAN, replies


def body_with_metadata():
    body=deepcopy(replies()[0]['response'])
    body['choices'][0]['message'].update(annotations=None,audio=None,function_call=None,
        reasoning='Synthetic inert reasoning metadata.',tool_calls=None)
    return body


@pytest.mark.parametrize('reasoning',[None,'','Synthetic explanatory metadata'])
@pytest.mark.parametrize('annotations',[None,[]])
def test_supported_optional_metadata_and_null_tools_are_normalized_without_mutating_raw(reasoning,annotations):
    body=body_with_metadata()
    body['choices'][0]['message'].update(reasoning=reasoning,annotations=annotations)
    original=deepcopy(body)
    message=providers.validate_assistant_choice(body)
    assert message['tool_calls']==[] and message is not body['choices'][0]['message']
    assert body==original and body['choices'][0]['message']['tool_calls'] is None
    assert validate_plan(providers.parse_model_json(message['content']))==PLAN


@pytest.mark.parametrize('field,value',[
    ('annotations',[{'type':'url_citation'}]),('annotations',{}),('annotations',''),
    ('audio',{}),('audio',{'data':'unsupported audio'}),
    ('function_call',{}),('function_call',{'name':'legacy','arguments':'{}'}),
    ('reasoning',False),('reasoning',{}),('reasoning',[]),
    ('reasoning_content',42),('unknown_optional',None),('unknown_optional','data'),
    ('tool_calls',{}),('tool_calls',''),('tool_calls',False),
])
def test_metadata_support_does_not_drop_nonempty_capabilities_or_unknown_fields(field,value):
    body=body_with_metadata()
    body['choices'][0]['message'][field]=value
    with pytest.raises(ValueError):
        providers.validate_assistant_choice(body,allow_tools=True)


@pytest.mark.parametrize('finish',['length','tool_calls','content_filter'])
def test_optional_metadata_never_bypasses_finish_reason_contract(finish):
    body=body_with_metadata()
    body['choices'][0]['finish_reason']=finish
    with pytest.raises(ValueError):
        providers.validate_assistant_choice(body,allow_tools=True)


@pytest.mark.parametrize('mutation',['wrong-model','truncated','unknown-field','audio','wrong-role'])
def test_http_success_with_an_unvalidated_envelope_is_inconclusive_not_a_regression(tmp_path,monkeypatch,mutation):
    body=body_with_metadata()
    choice=body['choices'][0]
    if mutation=='wrong-model': body['model']='unauthorized-model'
    if mutation=='truncated': choice['finish_reason']='length'
    if mutation=='unknown-field': choice['message']['unrecognized']=None
    if mutation=='audio': choice['message']['audio']={'data':'unsupported'}
    if mutation=='wrong-role': choice['message']['role']='user'
    raw={'status':'PASS','http_status':200,'http_attempted':True,'response':body}
    before=deepcopy(raw)
    transport=Mock(return_value=raw)
    monkeypatch.setattr(providers,'request',transport)
    result=run_live_workflow(tmp_path/'run')
    assert result['status']=='INCONCLUSIVE'
    assert result['requests'][0]['validation_status']=='FAIL'
    assert result['requests'][0]['validation_error']
    assert 'plan' not in result and 'verification' not in result
    saved=read_json(tmp_path/'run'/result['requests'][0]['evidence_file'])
    assert saved['response']==body and raw==before
    transport.assert_called_once()


def test_real_preserved_nebius_response_passes_envelope_and_plan_schema_without_rewriting_evidence():
    root=Path(__file__).resolve().parents[1]
    path=root/'outputs/submission-050/nebius-053-20261027/live-01/repair-proposal-1.json'
    if not path.exists():
        pytest.skip('Private local execution evidence is intentionally absent from public source-only checkouts')
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    record=read_json(path)
    body=record['response']
    providers.validate_response_model('nebius','nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B',body['model'])
    message=providers.validate_assistant_choice(body)
    plan=validate_plan(providers.parse_model_json(message['content']))
    # Envelope compatibility is not verification approval. This original plan
    # disables legacy behavior and must still fail the independent verifier.
    assert plan['preserve_legacy'] is False and verify_plan(plan)['status']=='REJECTED'
    assert read_json(path.with_name('report.json'))['status']=='FAIL'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before


def test_public_compatibility_requirements_reach_initial_and_revision_requests_without_editing_model_plans(tmp_path,monkeypatch):
    bad=replies()[0]
    bad['response']['choices'][0]['message']['content']=json.dumps({**PLAN,'preserve_legacy':False})
    queue=iter([bad]+replies())
    sent=[]
    def transport(provider,payload):
        sent.append(deepcopy(payload))
        return next(queue)
    monkeypatch.setattr(providers,'request',transport)
    report=run_live_workflow(tmp_path/'run')
    assert report['status']=='PASS' and len(sent)==4
    initial=json.loads(sent[0]['messages'][1]['content'])
    requirements=initial['requirements']
    assert requirements==report['proposal_requirements']
    assert 'additional_kwargs.tool_calls' in requirements['legacy_tool_calls']
    assert 'additional_kwargs.function_call' in requirements['legacy_function_call']
    assert 'Preserve' in requirements['normal_messages']
    assert all(name not in requirements for name in ('test_cases','expected','checks','preserve_legacy'))
    revision=json.loads(sent[1]['messages'][-1]['content'])
    assert revision['requirements']==requirements
    assert revision['public_counterexample_result']['status']=='PASS'
    assert report['repair_attempts'][0]['plan']['preserve_legacy'] is False
    assert report['repair_attempts'][0]['verification']['status']=='REJECTED'
    assert report['repair_attempts'][1]['plan']['preserve_legacy'] is True
    assert report['repair_attempts'][1]['verification']['status']=='VERIFIED'
    assert len(report['verification']['checks'])==8
