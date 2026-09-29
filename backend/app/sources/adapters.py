from .base import EvidenceSourceAdapter,SourceHealth
class CNRCManual(EvidenceSourceAdapter):
 source_id='cnrc_manual';display_name='CNRC / Sidjilcom manual verification';source_type='OFFICIAL_MANUAL'
 async def health_check(self):return SourceHealth.MANUAL_ONLY
 async def collect(self,claims):return []
class Domain(EvidenceSourceAdapter):
 source_id='domain';display_name='DNS / RDAP / TLS';source_type='PUBLIC_TECHNICAL'
 async def health_check(self):return SourceHealth.AVAILABLE
 async def collect(self,claims):return []
ADAPTERS=[CNRCManual(),Domain()]
