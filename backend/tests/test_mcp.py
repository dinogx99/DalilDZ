def test_mcp_server_imports_and_exposes_server_object():
    from app.mcp.server import mcp

    assert mcp is not None
