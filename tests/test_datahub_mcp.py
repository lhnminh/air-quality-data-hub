import datahub_mcp


def test_catalog_context_requires_explicit_mcp_configuration(monkeypatch):
    monkeypatch.delenv("DATAHUB_GMS_URL", raising=False)
    monkeypatch.delenv("DATAHUB_GMS_TOKEN", raising=False)

    result = datahub_mcp.inspect_airtrace_catalog()

    assert result["status"] == "not_configured"
    assert "DATAHUB_GMS_URL" in result["summary"]


def test_save_document_requires_an_explicit_write_opt_in(monkeypatch):
    monkeypatch.delenv("DATAHUB_MCP_WRITE_ENABLED", raising=False)

    result = datahub_mcp.save_investigation_document("example")

    assert result["status"] == "not_enabled"
