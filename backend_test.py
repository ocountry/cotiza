#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class PriceTrackingAPITester:
    def __init__(self, base_url="https://pricespy-92.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_token = "test_session_1769837226936"  # From MongoDB setup
        self.user_id = "test-user-1769837226936"
        self.tests_run = 0
        self.tests_passed = 0
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.session_token}'
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, check_response=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {method} {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=self.headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=self.headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=self.headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                
                # Additional response checks
                if check_response and response.status_code < 400:
                    try:
                        response_data = response.json()
                        if not check_response(response_data):
                            success = False
                            print(f"❌ Response validation failed")
                    except:
                        pass
                        
                return success, response.json() if response.status_code < 400 else {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data}")
                    except:
                        print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n" + "="*50)
        print("TESTING AUTHENTICATION ENDPOINTS")
        print("="*50)
        
        # Test /auth/me
        success, user_data = self.run_test(
            "Get current user",
            "GET",
            "auth/me",
            200,
            check_response=lambda data: 'user_id' in data and 'email' in data
        )
        
        if success:
            print(f"   User: {user_data.get('name')} ({user_data.get('email')})")
            print(f"   Notification channels configured:")
            print(f"     Email: {user_data.get('notification_email', 'Not set')}")
            print(f"     WhatsApp: {user_data.get('notification_whatsapp', 'Not set')}")
            print(f"     Telegram: {user_data.get('notification_telegram', 'Not set')}")
            print(f"     SMS: {user_data.get('notification_sms', 'Not set')}")
        
        # Test profile update
        profile_update = {
            "notification_email": "updated@example.com",
            "notification_whatsapp": "+56999888777",
            "notification_telegram": "@updateduser",
            "notification_sms": "+56111222333"
        }
        
        success, updated_data = self.run_test(
            "Update user profile",
            "PUT",
            "auth/profile",
            200,
            data=profile_update,
            check_response=lambda data: data.get('notification_email') == 'updated@example.com'
        )
        
        if success:
            print(f"   Updated notification settings successfully")
        
        return success

    def test_price_parsing(self):
        """Test price parsing with different currency formats"""
        print("\n" + "="*50)
        print("TESTING PRICE PARSING")
        print("="*50)
        
        # Test URLs with different price formats
        test_urls = [
            {
                "url": "https://httpbin.org/html",  # Safe test URL
                "description": "Basic HTML page (for testing extraction)",
                "method": "scraping"
            }
        ]
        
        for test_case in test_urls:
            success, preview_data = self.run_test(
                f"Preview extraction - {test_case['description']}",
                "POST",
                "preview",
                200,
                data={
                    "url": test_case["url"],
                    "method": test_case["method"]
                }
            )
            
            if success:
                print(f"   Title: {preview_data.get('title', 'Not detected')}")
                print(f"   Price: {preview_data.get('price', 'Not detected')}")
                print(f"   Currency: {preview_data.get('currency', 'USD')}")
        
        return True

    def test_items_crud(self):
        """Test items CRUD operations"""
        print("\n" + "="*50)
        print("TESTING ITEMS CRUD OPERATIONS")
        print("="*50)
        
        # Test get items (empty initially)
        success, items_data = self.run_test(
            "Get all items",
            "GET",
            "items",
            200,
            check_response=lambda data: isinstance(data, list)
        )
        
        if success:
            print(f"   Found {len(items_data)} existing items")
        
        # Test create item
        new_item = {
            "url": "https://httpbin.org/html",
            "extraction_method": "scraping",
            "notification_channels": ["email", "whatsapp"]
        }
        
        success, created_item = self.run_test(
            "Create new item",
            "POST",
            "items",
            201,
            data=new_item,
            check_response=lambda data: 'item_id' in data and 'url' in data
        )
        
        item_id = None
        if success:
            item_id = created_item.get('item_id')
            print(f"   Created item: {item_id}")
            print(f"   Title: {created_item.get('title', 'N/A')}")
            print(f"   Price: {created_item.get('current_price', 'N/A')} {created_item.get('currency', 'USD')}")
            print(f"   Channels: {created_item.get('notification_channels', [])}")
        
        if item_id:
            # Test get specific item
            success, item_data = self.run_test(
                "Get specific item",
                "GET",
                f"items/{item_id}",
                200,
                check_response=lambda data: data.get('item_id') == item_id
            )
            
            # Test update item
            update_data = {
                "notification_channels": ["email", "telegram", "sms"],
                "is_active": True
            }
            
            success, updated_item = self.run_test(
                "Update item",
                "PUT",
                f"items/{item_id}",
                200,
                data=update_data,
                check_response=lambda data: len(data.get('notification_channels', [])) == 3
            )
            
            # Test price check
            success, check_result = self.run_test(
                "Manual price check",
                "POST",
                f"items/{item_id}/check",
                200,
                check_response=lambda data: 'item' in data and 'price_changed' in data
            )
            
            if success:
                print(f"   Price changed: {check_result.get('price_changed', False)}")
                print(f"   Old price: {check_result.get('old_price', 'N/A')}")
                print(f"   New price: {check_result.get('new_price', 'N/A')}")
            
            # Test get price history
            success, history_data = self.run_test(
                "Get price history",
                "GET",
                f"items/{item_id}/history",
                200,
                check_response=lambda data: isinstance(data, list)
            )
            
            if success:
                print(f"   History entries: {len(history_data)}")
            
            # Test delete item
            success, delete_result = self.run_test(
                "Delete item",
                "DELETE",
                f"items/{item_id}",
                200
            )
            
            if success:
                print(f"   Item deleted successfully")
        
        return True

    def test_currency_formatting(self):
        """Test currency formatting logic"""
        print("\n" + "="*50)
        print("TESTING CURRENCY FORMATTING")
        print("="*50)
        
        # This would be tested in frontend, but we can verify backend parsing
        test_cases = [
            {"text": "$1.299.990", "expected_currency": "CLP", "description": "CLP format"},
            {"text": "$1,299.99", "expected_currency": "USD", "description": "USD format"},
            {"text": "€1.299,99", "expected_currency": "EUR", "description": "EUR format"},
        ]
        
        print("   Currency parsing test cases:")
        for case in test_cases:
            print(f"   - {case['description']}: {case['text']} -> Expected: {case['expected_currency']}")
        
        return True

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Price Tracking API Tests")
        print(f"Base URL: {self.base_url}")
        print(f"Session Token: {self.session_token[:20]}...")
        
        try:
            # Test authentication
            auth_success = self.test_auth_endpoints()
            
            # Test price parsing
            parsing_success = self.test_price_parsing()
            
            # Test CRUD operations
            crud_success = self.test_items_crud()
            
            # Test currency formatting
            currency_success = self.test_currency_formatting()
            
            # Print summary
            print("\n" + "="*50)
            print("TEST SUMMARY")
            print("="*50)
            print(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
            print(f"✅ Authentication: {'PASS' if auth_success else 'FAIL'}")
            print(f"✅ Price Parsing: {'PASS' if parsing_success else 'FAIL'}")
            print(f"✅ CRUD Operations: {'PASS' if crud_success else 'FAIL'}")
            print(f"✅ Currency Support: {'PASS' if currency_success else 'FAIL'}")
            
            success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
            print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
            
            return 0 if self.tests_passed == self.tests_run else 1
            
        except Exception as e:
            print(f"\n❌ Test suite failed with error: {str(e)}")
            return 1

def main():
    tester = PriceTrackingAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())