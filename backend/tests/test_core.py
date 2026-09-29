from app.core.domain import norm,ident,form,similarity,compare,Status
from app.services.security import validate_public_url
import pytest
def test_arabic():assert norm('بِئْرُ الـجِير')=='بير الجير'
def test_ident():assert ident('16 B-0123456')=='16B0123456'
def test_form():assert form('S.A.R.L Alpha')=='SARL'
def test_name():assert similarity('SARL ALPHA DISTRIBUTION','Alpha Distribution S.A.R.L')>.85
def test_rc_match():assert compare('rc','16B0123456','16 B 0123456')[0]==Status.VERIFIED
def test_rc_conflict():assert compare('rc','16B0123456','16B9999999')[0]==Status.CONFLICTING
@pytest.mark.parametrize('u',['http://localhost/x','http://127.0.0.1/x','http://169.254.169.254/latest'])
def test_ssrf(u):
 with pytest.raises(ValueError):validate_public_url(u)
