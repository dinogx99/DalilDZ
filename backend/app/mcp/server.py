"""DalilDZ MCP tool registry foundation."""
from ..core.domain import compare
TOOLS={'compare_business_claims':lambda field,submitted,observed:{'status':compare(field,submitted,observed)[0].value,'metadata':compare(field,submitted,observed)[1]},'resolve_algerian_entity':lambda a,b:{'field':'legal_name','result':compare('legal_name',a,b)[0].value}}
def list_tools():return sorted(TOOLS)
