import os,tempfile
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp('.db')
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db
init_db();c=TestClient(app)
def test_flow():
 r=c.post('/api/v1/cases',json={'name':'SYNTHETIC ALPHA','claims':{'rc':'16B0123456','legal_form':'SARL'}});assert r.status_code==201;cid=r.json()['id'];assert c.post(f'/api/v1/cases/{cid}/analyze').status_code==200;rep=c.get(f'/api/v1/cases/{cid}/report').json();assert rep['fingerprint'];assert 'trustworthy' in rep['disclaimer']
def test_sources():
 x=c.get('/api/v1/sources').json();assert any(i['health']=='MANUAL_ONLY' for i in x)
