from enum import StrEnum
from hashlib import sha256
import re,unicodedata,uuid,json
from rapidfuzz.fuzz import token_set_ratio
class Status(StrEnum):
 VERIFIED='VERIFIED';CONSISTENT='CONSISTENT';CONFLICTING='CONFLICTING';NOT_FOUND='NOT_FOUND';NOT_VERIFIABLE='NOT_VERIFIABLE';SOURCE_UNAVAILABLE='SOURCE_UNAVAILABLE';OUTDATED='OUTDATED';MANUAL_REVIEW_REQUIRED='MANUAL_REVIEW_REQUIRED'
FORMS={'SARL','EURL','SPA','SNC','SCS'}; AR=str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ى':'ي','ـ':''})
def norm(v):
 if not v:return None
 v=unicodedata.normalize('NFKD',v.translate(AR));v=''.join(c for c in v if not unicodedata.combining(c));return re.sub(r'\s+',' ',re.sub(r'[^\w\u0600-\u06ff]+',' ',v.lower())).strip()
def ident(v):return re.sub(r'[^A-Z0-9]','',v.upper()) if v else None
def form(v):
 u=re.sub(r'[^A-Z]','',v.upper()) if v else ''
 return next((x for x in FORMS if x in u),None)
def similarity(a,b):return round(token_set_ratio(norm(a) or '',norm(b) or '')/100,3)
def compare(field,a,b):
 if b is None:return Status.NOT_VERIFIABLE,{'reason':'No comparable evidence'}
 if a is None:return Status.CONSISTENT,{'reason':'Observed value only'}
 if field in {'rc','nif','nis','ai'}:return (Status.VERIFIED if ident(a)==ident(b) else Status.CONFLICTING),{'method':'exact_normalized_identifier'}
 if field=='legal_form':return (Status.VERIFIED if form(a)==form(b) else Status.CONFLICTING),{'method':'legal_form_normalization'}
 s=similarity(a,b);return (Status.CONSISTENT if s>=.88 else Status.CONFLICTING),{'method':'token_set_similarity','similarity':s}
def uid():return str(uuid.uuid4())
def fingerprint(o):return sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
