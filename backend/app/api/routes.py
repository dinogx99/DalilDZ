from fastapi import APIRouter,UploadFile,File,HTTPException
from pydantic import BaseModel,Field
from ..core.db import Session,Case,Document,Evidence
from ..core.domain import uid
from ..services.documents import process
from ..services.pipeline import analyze,report
from ..sources.adapters import ADAPTERS
r=APIRouter(prefix='/api/v1')
class CaseIn(BaseModel):name:str=Field(min_length=1,max_length=200);claims:dict[str,str]={}
@r.get('/health')
def health():return {'status':'ok','version':'1.0.0'}
@r.post('/cases',status_code=201)
def create(x:CaseIn):
 with Session() as db:
  c=Case(id=uid(),name=x.name,claims=x.claims);db.add(c);db.commit();return {'id':c.id,'name':c.name,'claims':c.claims}
@r.get('/cases/{cid}')
def get(cid):
 with Session() as db:
  c=db.get(Case,cid)
  if not c:raise HTTPException(404,'CASE_NOT_FOUND')
  return {'id':c.id,'name':c.name,'claims':c.claims}
@r.delete('/cases/{cid}',status_code=204)
def delete(cid):
 with Session() as db:
  c=db.get(Case,cid)
  if c:db.delete(c);db.commit()
@r.post('/cases/{cid}/documents',status_code=201)
async def upload(cid:str,file:UploadFile=File(...)):
 b=await file.read(10485761)
 if len(b)>10485760:raise HTTPException(413,'FILE_TOO_LARGE')
 try:m,h,t,x=process(b)
 except Exception as e:raise HTTPException(400,str(e))
 with Session() as db:
  if not db.get(Case,cid):raise HTTPException(404,'CASE_NOT_FOUND')
  d=Document(id=uid(),case_id=cid,filename=(file.filename or 'upload')[-200:],mime=m,sha256=h,text=t,extracted=x);db.add(d);db.commit();return {'id':d.id,'mime':m,'sha256':h,'extracted':x}
@r.post('/cases/{cid}/analyze')
def run(cid):
 with Session() as db:
  c=db.get(Case,cid)
  if not c:raise HTTPException(404,'CASE_NOT_FOUND')
  return {'findings':len(analyze(db,c,db.query(Document).filter_by(case_id=cid).all()))}
@r.get('/cases/{cid}/evidence')
def ev(cid):
 with Session() as db:return [{'field':e.field,'status':e.status,'submitted':e.submitted,'observed':e.observed,'source':e.source,'metadata':e.metadata_json} for e in db.query(Evidence).filter_by(case_id=cid).all()]
@r.get('/cases/{cid}/checks')
def checks(cid):return ev(cid)
@r.get('/cases/{cid}/report')
def rep(cid):
 with Session() as db:
  c=db.get(Case,cid)
  if not c:raise HTTPException(404,'CASE_NOT_FOUND')
  return report(c,db.query(Evidence).filter_by(case_id=cid).all())
@r.get('/sources')
async def sources():return [{'id':a.source_id,'name':a.display_name,'type':a.source_type,'health':(await a.health_check()).value} for a in ADAPTERS]
@r.get('/sources/health')
async def sh():return await sources()
