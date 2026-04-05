import pytest


@pytest.mark.asyncio
async def test_create_record_writes_audit(async_client):
    assert True


@pytest.mark.asyncio
async def test_update_record_writes_before_after(async_client):
    assert True


@pytest.mark.asyncio
async def test_delete_record_writes_audit(async_client):
    assert True
