"""
Contract tests for GHL Locations API
Tests the API contract without implementation
Following TDD: These tests should FAIL before implementation
"""
import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
class TestGHLLocationsAPI:
    """Test suite for /ghl/locations endpoint"""

    async def test_get_locations_returns_200(self, async_client: AsyncClient):
        """Test GET /ghl/locations returns 200 OK"""
        response = await async_client.get("/ghl/locations")
        assert response.status_code == status.HTTP_200_OK

    async def test_get_locations_returns_list(self, async_client: AsyncClient):
        """Test GET /ghl/locations returns a list of locations"""
        response = await async_client.get("/ghl/locations")
        data = response.json()

        assert "locations" in data
        assert isinstance(data["locations"], list)

    async def test_get_location_schema_fields(self, async_client: AsyncClient):
        """Test location objects contain required fields per OpenAPI spec"""
        response = await async_client.get("/ghl/locations")
        data = response.json()

        if len(data["locations"]) > 0:
            location = data["locations"][0]

            # Required fields from ghl-locations-api.yaml
            assert "ghl_location_id" in location
            assert "name" in location
            assert "company_id" in location
            assert "has_whatsapp" in location
            assert "is_active" in location

            # Optional fields
            assert "whatsapp_number" in location or location.get("whatsapp_number") is None
            assert "whatsapp_status" in location or location.get("whatsapp_status") is None

    async def test_get_location_by_id_returns_200(self, async_client: AsyncClient):
        """Test GET /ghl/locations/{location_id} returns 200 OK for valid ID"""
        # First, get a valid location ID
        response = await async_client.get("/ghl/locations")
        data = response.json()

        # Skip test if no locations exist
        if len(data["locations"]) == 0:
            pytest.skip("No locations available for testing")

        location_id = data["locations"][0]["ghl_location_id"]

        # Get specific location
        response = await async_client.get(f"/ghl/locations/{location_id}")
        assert response.status_code == status.HTTP_200_OK

    async def test_get_location_by_id_returns_404_for_invalid_id(self, async_client: AsyncClient):
        """Test GET /ghl/locations/{location_id} returns 404 for non-existent ID"""
        response = await async_client.get("/ghl/locations/invalid_location_id_12345")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_location_by_id_returns_single_object(self, async_client: AsyncClient):
        """Test GET /ghl/locations/{location_id} returns a single location object"""
        # First, get a valid location ID
        response = await async_client.get("/ghl/locations")
        data = response.json()

        if len(data["locations"]) == 0:
            pytest.skip("No locations available for testing")

        location_id = data["locations"][0]["ghl_location_id"]

        # Get specific location
        response = await async_client.get(f"/ghl/locations/{location_id}")
        data = response.json()

        # Should return single object, not wrapped in array
        assert "ghl_location_id" in data
        assert data["ghl_location_id"] == location_id

    async def test_filter_active_locations_only(self, async_client: AsyncClient):
        """Test GET /ghl/locations?active=true returns only active locations"""
        response = await async_client.get("/ghl/locations?active=true")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        # All returned locations should be active
        for location in data["locations"]:
            assert location["is_active"] is True

    async def test_filter_locations_with_whatsapp(self, async_client: AsyncClient):
        """Test GET /ghl/locations?whatsapp=true returns only WhatsApp-enabled locations"""
        response = await async_client.get("/ghl/locations?whatsapp=true")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        # All returned locations should have WhatsApp enabled
        for location in data["locations"]:
            assert location["has_whatsapp"] is True

    async def test_combined_filters(self, async_client: AsyncClient):
        """Test GET /ghl/locations with multiple filters"""
        response = await async_client.get("/ghl/locations?active=true&whatsapp=true")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK

        # All returned locations should match both filters
        for location in data["locations"]:
            assert location["is_active"] is True
            assert location["has_whatsapp"] is True
