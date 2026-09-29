from ..core.domain import compare,Status,uid,fingerprint
from ..core.db import Evidence
def analyze(db,case,docs):
 db.query(Evidence).filter(Evidence.case_id==case.id).delete();out=[]
 for d in docs:
  for f,v in d.extracted.items():
   s,m=compare(f,case.claims.get(f),v);e=Evidence(id=uid(),case_id=case.id,field=f,submitted=case.claims.get(f),observed=str(v),status=s.value,source='document:'+d.id,metadata_json={**m,'document':d.filename,'sha256':d.sha256});db.add(e);out.append(e)
 for f,v in case.claims.items():
  if not any(e.field==f for e in out):
   e=Evidence(id=uid(),case_id=case.id,field=f,submitted=str(v),observed=None,status=Status.NOT_VERIFIABLE.value,source='no_automated_source',metadata_json={'reason':'Manual verification may be required'});db.add(e);out.append(e)
 db.commit();return out
def report(c,es):
 rows=[{'field':e.field,'submitted':e.submitted,'observed':e.observed,'status':e.status,'source':e.source,'metadata':e.metadata_json} for e in es];p={'version':'1.0.0','case':{'id':c.id,'name':c.name,'claims':c.claims},'findings':rows,'disclaimer':'DalilDZ does not determine whether an entity is trustworthy, solvent, legitimate, fraudulent, or safe.'};p['fingerprint']=fingerprint(p);return p
