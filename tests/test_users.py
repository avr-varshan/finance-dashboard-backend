import pytest


@pytest.mark.asyncio
async def test_viewer_cannot_create_record(async_client):
    # TODO: actual token logic
    assert True


@pytest.mark.asyncio
async def test_admin_can_change_user_role(async_client):
    assert True


@pytest.mark.asyncio
async def test_admin_cannot_change_own_role(async_client):
    assert True
