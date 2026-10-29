"""Loopback-only, fixed-workflow demo. No arbitrary code, files or prompts accepted."""
from copy import deepcopy
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from uuid import uuid4
from .live_workflow import MAX_WORKFLOW_STEPS, WorkflowUnavailable, run_live_workflow, validate_workflow_limits
from .evidence import sanitize
from . import providers

def serve_live_demo(output='outputs/live-demo',port=8780,provider='glm',model=None,use_tavily=False,knowledge_dir=None,
                    budget_path=None,max_runs=0,**options):
    configuration=validate_workflow_limits(**options)
    if type(max_runs) is not int or max_runs < 0:
        raise ValueError('max_runs must be a nonnegative integer; 0 means unlimited user-started runs')
    configuration['max_output_tokens']=providers.validate_output_tokens(provider,configuration['max_output_tokens']
        if configuration['max_output_tokens'] is not None else (2048 if provider=='nebius' else 4096))
    selected=providers.select_model(provider,model,require_nemotron=provider=='nebius')
    budget=None
    if budget_path is not None:
        from .budget import RequestBudget
        budget=RequestBudget.from_existing(budget_path) if Path(budget_path).exists() else RequestBudget(budget_path)
    public_limits={**configuration,'max_runs':max_runs,'persistent_budget_enabled':budget is not None,
                   'persistent_budget_limits':dict(budget.limits) if budget else None}
    root=Path(output).resolve();root.mkdir(parents=True,exist_ok=True)
    token=secrets.token_urlsafe(32)
    lock=threading.Lock()
    state={'status':'IDLE','events':[],'report':None,'runs':0,'provider':provider,'model':selected,'use_tavily':use_tavily,
        'knowledge_enabled':knowledge_dir is not None,'limits':public_limits}
    origin=f'http://127.0.0.1:{port}'
    def observe(event):
        with lock: state['events'].append(event)
    def execute():
        try:
            with budget.applied() if budget else nullcontext():
                result=run_live_workflow(root/('run-'+uuid4().hex[:12]),observe,provider=provider,model=selected,
                    use_tavily=use_tavily,knowledge_dir=knowledge_dir,**configuration)
            if not isinstance(result,dict) or result.get('status') not in {'PASS','FAIL','BLOCKED','INCONCLUSIVE'}:
                raise ValueError('Workflow did not return a supported terminal status')
            with lock: state.update(status=result['status'],report=result)
        except WorkflowUnavailable as exc:
            with lock: state.update(status=exc.status,report=None,error=sanitize(type(exc).__name__+': '+str(exc)))
        except Exception as exc:
            with lock: state.update(status='INCONCLUSIVE',report=None,error=sanitize(type(exc).__name__+': '+str(exc)))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def authorized_host(self): return self.headers.get('Host','')==f'127.0.0.1:{port}'
        def send(self,status,payload,mime='application/json; charset=utf-8'):
            data=payload if isinstance(payload,bytes) else json.dumps(sanitize(payload),ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if not self.authorized_host(): return self.send(403,{'error':'Invalid host'})
            if self.path=='/': return self.send(200,(Path(__file__).parent/'web/live.html').read_bytes(),'text/html; charset=utf-8')
            if self.path=='/session': return self.send(200,{'session':token,'provider':provider,'model':selected,
                'use_tavily':use_tavily,'knowledge_enabled':knowledge_dir is not None,'limits':public_limits})
            if self.path=='/state':
                with lock: snapshot=deepcopy(state)
                return self.send(200,snapshot)
            return self.send(404,{'error':'Not found'})
        def do_POST(self):
            if not self.authorized_host() or self.headers.get('Origin')!=origin or not secrets.compare_digest(self.headers.get('X-PatchCourt-Session',''),token):
                return self.send(403,{'error':'Local session required'})
            if self.path!='/run': return self.send(404,{'error':'Not found'})
            if self.headers.get('Content-Type')!='application/json' or self.headers.get('Content-Length')!='2' or self.rfile.read(2)!=b'{}':
                return self.send(400,{'error':'Only the fixed empty workflow request is allowed'})
            with lock:
                if state['status']=='RUNNING': return self.send(409,{'error':'Run already active'})
                if max_runs and state['runs']>=max_runs: return self.send(429,{'error':f'{max_runs}-run server budget exhausted; a supplied persistent ledger is never reset by restarting'})
                state.update(status='RUNNING',events=[],report=None,runs=state['runs']+1)
                state.pop('error',None)
            try:
                threading.Thread(target=execute,daemon=True).start()
            except Exception as exc:
                with lock: state.update(status='INCONCLUSIVE',error=sanitize(type(exc).__name__+': '+str(exc)))
                return self.send(503,{'error':'Workflow could not start. Inspect server status; no automatic retry was started.'})
            return self.send(202,{'status':'RUNNING'})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'ReviKnot live demo: {origin} ({provider}: {selected or "NVIDIA Nemotron discovery"})',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
