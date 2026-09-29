from abc import ABC,abstractmethod
from enum import StrEnum
class SourceHealth(StrEnum):AVAILABLE='AVAILABLE';DEGRADED='DEGRADED';UNAVAILABLE='UNAVAILABLE';MANUAL_ONLY='MANUAL_ONLY'
class EvidenceSourceAdapter(ABC):
 source_id='';display_name='';source_type=''
 @abstractmethod
 async def health_check(self):...
 @abstractmethod
 async def collect(self,claims):...
