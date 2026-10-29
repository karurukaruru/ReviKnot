"""Untrusted model text and bounded dispatch accounting; synthetic transport only."""
import json
from unittest.mock import Mock

import pytest

from patchcourt import providers
from patchcourt.budget import RequestBudget
from patchcourt.evidence import digest, read_json
from patchcourt.live_workflow import Session, WorkflowUnavailable, run_live_workflow
from patchcourt.source_review import run_source_review
from tests.test_patchcourt_live_workflow import replies


@pytest.mark.parametrize('wrapper', [
    '{}', '```json\n{}\n```', 'Explanation first.\n```\n{}\n```\nNo code is executed.',
    'Here is the result:\n{}\nThis is an unverified suggestion.',
    '````JSON\n{}\n````', '~~~json\n{}\n~~~',
])
def test_single_json_container_can_be_recovered_without_changing_its_values(wrapper):
    value={'issues': [], 'note': 'Brackets [] and escaped "quotes" inside a string: \\ and 中文 {}'}
    assert providers.parse_model_json(wrapper.format(json.dumps(value))) == value


@pytest.mark.parametrize('content', [
    'Result: {"issues":[],"issues":[]}',
    '```json\n{"score":NaN}\n```',
    'Result: {"score":Infinity}',
    'Result: {"score":1e999}',
    'Result: []\nAlternative: []',
    'Result: {"issues":[]} then {"issues":[]}',
    'Result: {"issues":[]',
    'Result: {"issues":[}]',
    'Result: {\'issues\':[]}',
    '"[]" followed by commentary',
    '```json\n[]',
    '```python\n[]\n```',
    '```json\n[]\n```\n```python\npass\n```',
    'Result: []\n}',
    'Result: ' + '['*66 + '0' + ']'*66,
])
def test_recovery_never_repairs_invalid_json_or_chooses_an_ambiguous_answer(content):
    with pytest.raises(ValueError):
        providers.parse_model_json(content)


def test_model_json_recovery_retains_size_bounds():
    with pytest.raises(ValueError, match='exceeds'):
        providers.parse_model_json('Explanation. '+json.dumps({'text':'x'*providers.MAX_BYTES}))


def test_wrapped_source_review_keeps_schema_and_raw_evidence(tmp_path, monkeypatch):
    source=tmp_path/'sample.py'
    source.write_text('raise RuntimeError("source must never execute")\n', encoding='utf-8')
    content='Here is the review:\n```json\n{"issues":[]}\n```\nNo verified claims.'
    record={'status':'PASS','provider':'deepseek','response':{'model':providers.DEEPSEEK_MODEL,'choices':[
        {'finish_reason':'stop','message':{'role':'assistant','content':content}}]}}
    monkeypatch.setattr(providers,'request',lambda *args, **kwargs:record)
    report=run_source_review(source,tmp_path/'review')
    assert report['status']=='COMPLETE'
    saved=read_json(tmp_path/'review'/report['chunks'][0]['response_file'])
    assert saved['response']['choices'][0]['message']['content']==content
    record['response']['choices'][0]['message']['content']='Result: {"issues":[],"unknown":true}'
    assert run_source_review(source,tmp_path/'bad-schema')['status']=='FAIL'


@pytest.mark.parametrize('outer',[
    lambda plan:'Result: {"outer":invalid,"nested":'+plan+'}',
    lambda plan:'Result: {"outer":'+plan+',"outer":'+plan+'}',
    lambda plan:'Result: {"outer":'+plan,
])
def test_invalid_outer_json_never_promotes_its_valid_nested_mapping(tmp_path,monkeypatch,outer):
    values=replies()
    message=values[0]['response']['choices'][0]['message']
    message['content']=outer(message['content'])
    transport=Mock(return_value=values[0])
    monkeypatch.setattr(providers,'request',transport)
    result=run_live_workflow(tmp_path/'invalid-outer')
    assert result['status']=='FAIL' and 'plan' not in result
    transport.assert_called_once()


def test_wrapped_live_plan_and_final_answer_pass_but_tool_arguments_stay_strict(tmp_path, monkeypatch):
    values=replies()
    for index in (0,2):
        message=values[index]['response']['choices'][0]['message']
        message['content']='Explanation.\n```json\n'+message['content']+'\n```\nData only.'
    queue=iter(values)
    monkeypatch.setattr(providers,'request',lambda *args, **kwargs:next(queue))
    report=run_live_workflow(tmp_path/'wrapped')
    assert report['status']=='PASS' and len(report['requests'])==3
    assert report['request_accounting']['requests_with_unknown_http_attempt']==3
    assert report['request_accounting']['http_attempts_total']==0
    values=replies()
    values[1]['response']['choices'][0]['message']['tool_calls'][0]['function']['arguments']='```json\n{"sku":"A"}\n```'
    queue=iter(values)
    assert run_live_workflow(tmp_path/'strict-tool-arguments')['status']=='FAIL'


def test_all_three_dispatch_kinds_use_the_existing_ledger_once_and_report_separately(tmp_path, monkeypatch):
    model='nvidia/Nemotron-synthetic-accounting'
    monkeypatch.delenv('NEBIUS_MODEL',raising=False)
    values=replies()
    for value in values:
        value['response']['model']=model
        value['http_attempted']=True  # Synthetic transport marker; never a real request.
    queue=iter(values)
    calls=[]
    def transport(provider,payload=None,endpoint='chat/completions'):
        calls.append((provider,endpoint))
        if endpoint=='models':
            return {'status':'PASS','http_attempted':True,'response':{'data':[{'id':model}]}}
        if provider=='tavily':
            return {'status':'PASS','http_attempted':True,'usage':{'credits':1},'response':{'results':[
                {'url':'https://docs.langchain.com/oss/python/langchain/messages','content':'Synthetic bounded documentation.'}]}}
        return next(queue)
    monkeypatch.setattr(providers,'request',transport)
    ledger=RequestBudget(tmp_path/'budget.json',model_calls=3,searches=1,discovery_calls=1)
    with ledger.applied():
        report=run_live_workflow(tmp_path/'run',provider='nebius',use_tavily=True)
    assert report['status']=='PASS'
    accounting=report['request_accounting']
    assert accounting['reservations_by_kind']=={'model':3,'search':1,'discovery':1}
    assert accounting['total_reserved_requests']==accounting['http_attempts_total']==5
    assert accounting['http_attempts_by_kind']==accounting['reservations_by_kind']
    assert accounting['requests_with_unknown_http_attempt']==0
    assert len(report['requests'])==3 and len(report['auxiliary_requests'])==2
    assert report['total_reported_tokens']==30  # Search credits are never model tokens.
    assert report['reserved_token_upper_estimate']==sum(row['reserved'] for row in report['requests'])
    assert report['limits']['max_model_requests']==16 and report['limits']['max_provider_requests']==18
    assert [row['kind'] for row in ledger.state['reservations']]==[
        'discovery_calls','searches','model_calls','model_calls','model_calls']
    assert len(calls)==5 and all(ledger.remaining(kind)==0 for kind in ledger.limits)
    for row in report['auxiliary_requests']:
        assert row['evidence_sha256']==digest(read_json(tmp_path/'run'/row['evidence_file']))
    assert read_json(tmp_path/'run/manifest.json')['report_sha256']==digest(read_json(tmp_path/'run/report.json'))


@pytest.mark.parametrize('kind',['model','search','discovery'])
@pytest.mark.parametrize('provider_status,attempted,expected',[
    ('BLOCKED',False,'BLOCKED'),('FAIL',True,'INCONCLUSIVE'),
])
def test_unavailable_provider_is_not_mislabeled_an_executed_regression(tmp_path, monkeypatch, kind, provider_status, attempted, expected):
    monkeypatch.delenv('NEBIUS_MODEL',raising=False)
    monkeypatch.setattr(providers,'request',lambda *args,**kwargs:{
        'status':provider_status,'http_attempted':attempted,'reason':'Synthetic prerequisite unavailable'})
    report=run_live_workflow(tmp_path/'run',provider='nebius' if kind=='discovery' else 'glm',use_tavily=kind=='search')
    assert report['status']==expected
    assert report['request_accounting']['reservations_by_kind']=={name:int(name==kind) for name in ('model','search','discovery')}
    assert report['request_accounting']['http_attempts_total']==int(attempted)


def test_exhausted_persistent_ledger_blocks_transport_without_refunding_local_dispatch(tmp_path,monkeypatch):
    transport=Mock()
    monkeypatch.setattr(providers,'request',transport)
    ledger=RequestBudget(tmp_path/'budget.json',model_calls=0)
    with ledger.applied():
        report=run_live_workflow(tmp_path/'run')
    transport.assert_not_called()
    assert report['status']=='INCONCLUSIVE'
    assert report['request_accounting']['total_reserved_requests']==1
    assert report['request_accounting']['http_attempts_total']==0
    assert ledger.state['reservations']==[]


def test_session_model_and_auxiliary_hard_limits_stop_before_dispatch(tmp_path,monkeypatch):
    value=replies()[0]
    transport=Mock(return_value=value)
    monkeypatch.setattr(providers,'request',transport)
    session=Session(tmp_path/'run',use_tavily=True,max_model_requests=8)
    for index in range(8):
        session.call('call-'+str(index),[])
    with pytest.raises(WorkflowUnavailable,match='budget exhausted'):
        session.call('over-limit',[])
    assert transport.call_count==8
    operation=Mock(return_value={'status':'FAIL','http_attempted':False})
    session.auxiliary_call('search-1','search',operation)
    with pytest.raises(WorkflowUnavailable,match='budget exhausted'):
        session.auxiliary_call('search-2','search',operation)
    assert operation.call_count==1
    with pytest.raises(WorkflowUnavailable):
        session.auxiliary_call('disabled-discovery','discovery',operation)
    assert operation.call_count==1


def test_provider_marks_missing_key_and_transport_attempts_explicitly(monkeypatch):
    monkeypatch.delenv('GLM_API_KEY',raising=False)
    transport=Mock(return_value=(503,{},'unavailable'))
    monkeypatch.setattr(providers,'_transport',transport)
    payload=providers.completion_payload('glm',[])
    blocked=providers.request('glm',payload)
    assert blocked['status']=='BLOCKED' and blocked['http_attempted'] is False
    transport.assert_not_called()
    monkeypatch.setenv('GLM_API_KEY','synthetic-accounting-fixture-key')
    attempted=providers.request('glm',payload)
    assert attempted['status']=='FAIL' and attempted['http_attempted'] is True
    assert attempted['request_kind']=='model'
    transport.assert_called_once()
