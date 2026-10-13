from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
import json, uuid, threading, logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.engine import Story, Prompt, storyboard, render

ROOT=Path(__file__).resolve().parents[1]/'data'
ROOT.mkdir(exist_ok=True)
lock=threading.Lock()
executor=ThreadPoolExecutor(max_workers=1)

def save(id, value):
    path=ROOT/id/'job.json'
    with lock:
        tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(value)); tmp.replace(path)

def load(id):
    try: uuid.UUID(id)
    except ValueError: raise HTTPException(404,'Job not found')
    path=ROOT/id/'job.json'
    if not path.exists(): raise HTTPException(404,'Job not found')
    return json.loads(path.read_text())

@asynccontextmanager
async def lifespan(app):
    # Interrupted jobs are explicitly marked failed, never stuck forever.
    for p in ROOT.glob('*/job.json'):
        job=json.loads(p.read_text())
        if job['status'] in ['queued','rendering']:
            job.update(status='failed',error='Render interrupted by restart. Submit again.'); save(p.parent.name,job)
    yield
    executor.shutdown(wait=True)

app=FastAPI(title='Cartoon Studio',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['GET','POST'],allow_headers=['Content-Type'])

@app.get('/health')
def health(): return {'status':'ok'}

@app.post('/api/storyboard',response_model=Story)
def plan(request:Prompt):
    try: return storyboard(request)
    except Exception:
        logging.exception('Story provider failed')
        raise HTTPException(502,'Story provider failed. Check Ollama is running and the model is installed.')

def work(id,story):
    job=load(id); job['status']='rendering'; save(id,job)
    def progress(value): job['progress']=value; save(id,job)
    try:
        render(story,ROOT/id,progress)
        job.update(status='completed',video=f'/api/jobs/{id}/video',error=None)
    except Exception:
        logging.exception('Render failed')
        job.update(status='failed',error='Rendering failed. Check backend logs and FFmpeg.')
    save(id,job)

@app.post('/api/jobs',status_code=202)
def create(story:Story):
    # Keep local rendering bounded; do not accumulate unlimited frame jobs.
    with lock:
        active=sum(json.loads(p.read_text())['status'] in ['queued','rendering'] for p in ROOT.glob('*/job.json'))
        if active>=3: raise HTTPException(429,'Render queue full. Try again after a job finishes.')
        id=str(uuid.uuid4()); (ROOT/id).mkdir()
        job={'id':id,'status':'queued','progress':0,'title':story.title,'error':None}
        (ROOT/id/'job.json').write_text(json.dumps(job))
    executor.submit(work,id,story); return job

@app.get('/api/jobs/{id}')
def status(id:str): return load(id)

@app.get('/api/jobs/{id}/video')
def video(id:str):
    if load(id)['status']!='completed': raise HTTPException(409,'Video not ready')
    return FileResponse(ROOT/id/'video.mp4',media_type='video/mp4',filename='cartoon.mp4')
