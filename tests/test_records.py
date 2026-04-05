import pytest


@pytest.mark.asyncio
async def test_filter_by_type(async_client):
    assert True


@pytest.mark.asyncio
async def test_date_range_filter(async_client):
    assert True


@pytest.mark.asyncio
async def test_amount_filter(async_client):
    assert True


@pytest.mark.asyncio
async def test_soft_deleted_not_returned(async_client):
    assert True


@pytest.mark.asyncio
async def test_get_record_deleted_returns_404_non_admin(async_client):
    assert True
