from app.core.tool_builder import OpenAPIImporter, SAMPLE_DEV_OPS_SWAGGER
from app.core.registry import registry

def test_openapi_importer():
    spec_data = OpenAPIImporter.parse_spec_content(SAMPLE_DEV_OPS_SWAGGER)
    tools, metadata = OpenAPIImporter.import_spec(
        spec_data=spec_data,
        target_agent_id="it_agent",
        auto_register=True
    )
    assert len(tools) >= 3
    
    # Verify Read vs Write
    status_tool = next((t for t in tools if "status" in t.name), None)
    rollback_tool = next((t for t in tools if "rollback" in t.name), None)

    assert status_tool is not None
    assert not status_tool.is_write
    assert not status_tool.require_confirmation

    assert rollback_tool is not None
    assert rollback_tool.is_write
    assert rollback_tool.require_confirmation

    # Verify registration
    assert registry.get_tool(status_tool.name) is not None

if __name__ == "__main__":
    test_openapi_importer()
    print("All tool builder tests passed successfully!")
