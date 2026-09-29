import io,re,hashlib
from pypdf import PdfReader
from PIL import Image
PAT={'rc':r'(?i)\bRC\s*[:#-]?\s*([0-9]{2}\s*[A-Z]\s*[0-9]{5,10})','nif':r'(?i)\bNIF\s*[:#-]?\s*([0-9]{10,20})','nis':r'(?i)\bNIS\s*[:#-]?\s*([0-9]{8,20})','email':r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}','website':r'https?://[^\s)]+'}
def sniff(b):
 if b.startswith(b'%PDF'):return 'application/pdf'
 if b.startswith(b'\xff\xd8\xff'):return 'image/jpeg'
 if b.startswith(b'\x89PNG'):return 'image/png'
 if b[:4]==b'RIFF' and b[8:12]==b'WEBP':return 'image/webp'
 raise ValueError('UNSUPPORTED_FILE_TYPE')
def process(b):
 m=sniff(b);text='\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(b))) if m=='application/pdf' else ''
 if m!='application/pdf':Image.open(io.BytesIO(b)).verify()
 out={}
 for k,p in PAT.items():
  x=re.search(p,text);out[k]=x.group(1 if x.lastindex else 0).strip() if x else None
 x=re.search(r'(?i)\b(SARL|EURL|SPA|SNC|SCS)\b',text);out['legal_form']=x.group(1).upper() if x else None
 return m,hashlib.sha256(b).hexdigest(),text,{k:v for k,v in out.items() if v}
