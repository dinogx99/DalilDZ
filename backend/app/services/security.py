import ipaddress,socket
from urllib.parse import urlparse
def validate_public_url(url):
 u=urlparse(url)
 if u.scheme not in {'http','https'} or not u.hostname or u.hostname.lower() in {'localhost','metadata.google.internal','169.254.169.254'}:raise ValueError('SSRF_BLOCKED')
 try: infos=socket.getaddrinfo(u.hostname,u.port or (443 if u.scheme=='https' else 80),type=socket.SOCK_STREAM)
 except socket.gaierror:raise ValueError('DNS_FAILED')
 if any(not ipaddress.ip_address(x[4][0]).is_global for x in infos):raise ValueError('SSRF_BLOCKED')
 return url
