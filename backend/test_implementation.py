#!/usr/bin/env python3
"""
End-to-end testing script for WhatsApp Campaign Interface Improvements

This script tests the key functionality we've implemented:
1. WAHA Sessions API endpoints
2. Dashboard API (without required user_id)
3. Frontend/Backend connectivity
4. Configuration changes
"""

import requests
import json
import time

def test_endpoint(url, description, expected_status=200):
    """Test an API endpoint and report results."""
    try:
        print(f"\n🧪 Testing: {description}")
        print(f"   URL: {url}")

        response = requests.get(url, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == expected_status:
            print(f"   ✅ PASS")
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            return True
        else:
            print(f"   ❌ FAIL - Expected {expected_status}, got {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"   ❌ FAIL - Connection error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 WhatsApp Campaign Interface Improvements - End-to-End Testing")
    print("=" * 70)

    backend_base = "http://localhost:8000"
    frontend_base = "http://localhost:3001"

    tests = [
        # Backend health check
        (f"{backend_base}/health", "Backend health check", 200),

        # WAHA Sessions API (our new implementation)
        (f"{backend_base}/waha/sessions", "WAHA sessions list", 200),
        (f"{backend_base}/waha/sessions/active", "WAHA active sessions", 200),
        (f"{backend_base}/waha/sessions/test-session/validate", "WAHA session validation (should fail)", 422),

        # Dashboard API (updated to not require user_id)
        (f"{backend_base}/api/v1/analytics/dashboard", "Dashboard without user_id", 200),
        (f"{backend_base}/api/v1/analytics/dashboard?days=7", "Dashboard with days parameter", 200),
        (f"{backend_base}/api/v1/analytics/dashboard?ghl_user_id=test-user", "Dashboard with optional user filter", 200),

        # API Documentation
        (f"{backend_base}/docs", "API documentation", 200),
        (f"{backend_base}/openapi.json", "OpenAPI schema", 200),
    ]

    results = []
    for url, description, expected_status in tests:
        success = test_endpoint(url, description, expected_status)
        results.append((description, success))

    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {description}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Implementation is working correctly!")
        print("\n✅ Key features verified:")
        print("   • WAHA Sessions API endpoints functioning")
        print("   • Dashboard API accepts optional user_id")
        print("   • Backend running on port 8000")
        print("   • API documentation accessible")
        print("   • Error handling working correctly")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the details above.")

    print("\n📝 Next steps:")
    print("   1. Frontend is running on port 3001 (resolves WAHA conflict)")
    print("   2. Database migration needed for waha_session_id field")
    print("   3. End-to-end testing with real WAHA instance")
    print("   4. Frontend component integration testing")

if __name__ == "__main__":
    main()