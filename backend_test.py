import requests
import sys
import json
from datetime import datetime

class PriceSpyAPITester:
    def __init__(self, base_url="https://pricespy-92.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.session_token:
            test_headers['Authorization'] = f'Bearer {self.session_token}'
        
        if headers:
            test_headers.update(headers)

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Method: {method}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json() if response.text else {}
                    self.log_test(name, True)
                    return True, response_data
                except:
                    self.log_test(name, True, "No JSON response")
                    return True, {}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('detail', '')}"
                except:
                    error_msg += f" - {response.text[:200]}"
                
                self.log_test(name, False, error_msg)
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def create_test_user_session(self):
        """Create test user and session using MongoDB"""
        print("\n🔧 Creating test user and session...")
        
        import subprocess
        import time
        
        # Generate unique identifiers
        timestamp = int(time.time())
        user_id = f"test-user-{timestamp}"
        session_token = f"test_session_{timestamp}"
        email = f"test.user.{timestamp}@example.com"
        
        # MongoDB command to create test user and session
        mongo_cmd = f'''
        use('test_database');
        db.users.insertOne({{
          user_id: "{user_id}",
          email: "{email}",
          name: "Test User",
          picture: "https://via.placeholder.com/150",
          created_at: new Date()
        }});
        db.user_sessions.insertOne({{
          user_id: "{user_id}",
          session_token: "{session_token}",
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        '''
        
        try:
            result = subprocess.run(
                ['mongosh', '--eval', mongo_cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.session_token = session_token
                self.user_id = user_id
                print(f"✅ Test user created: {user_id}")
                print(f"✅ Session token: {session_token}")
                return True
            else:
                print(f"❌ Failed to create test user: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Exception creating test user: {e}")
            return False

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_auth_me_without_token(self):
        """Test /auth/me without token (should fail)"""
        return self.run_test("Auth Me (No Token)", "GET", "auth/me", 401)

    def test_auth_me_with_token(self):
        """Test /auth/me with valid token"""
        if not self.session_token:
            self.log_test("Auth Me (With Token)", False, "No session token available")
            return False, {}
        return self.run_test("Auth Me (With Token)", "GET", "auth/me", 200)

    def test_items_list_empty(self):
        """Test getting items list (should be empty initially)"""
        return self.run_test("Items List (Empty)", "GET", "items", 200)

    def test_preview_extraction(self):
        """Test preview extraction endpoint"""
        test_data = {
            "url": "https://www.amazon.com/dp/B08N5WRWNW",
            "method": "scraping"
        }
        return self.run_test("Preview Extraction", "POST", "preview", 200, test_data)

    def test_create_item(self):
        """Test creating a new tracked item"""
        test_data = {
            "url": "https://www.amazon.com/dp/B08N5WRWNW",
            "extraction_method": "scraping",
            "notification_channels": ["email"],
            "notification_endpoint": "https://webhook.site/test"
        }
        success, response = self.run_test("Create Item", "POST", "items", 201, test_data)
        if success and response.get('item_id'):
            self.test_item_id = response['item_id']
            return True, response
        return success, response

    def test_get_items_with_data(self):
        """Test getting items list after creating one"""
        return self.run_test("Items List (With Data)", "GET", "items", 200)

    def test_get_item_detail(self):
        """Test getting specific item details"""
        if not hasattr(self, 'test_item_id'):
            self.log_test("Get Item Detail", False, "No test item ID available")
            return False, {}
        return self.run_test("Get Item Detail", "GET", f"items/{self.test_item_id}", 200)

    def test_update_item(self):
        """Test updating item settings"""
        if not hasattr(self, 'test_item_id'):
            self.log_test("Update Item", False, "No test item ID available")
            return False, {}
        
        update_data = {
            "notification_channels": ["email", "telegram"],
            "is_active": True
        }
        return self.run_test("Update Item", "PUT", f"items/{self.test_item_id}", 200, update_data)

    def test_check_item_price(self):
        """Test manual price check"""
        if not hasattr(self, 'test_item_id'):
            self.log_test("Check Item Price", False, "No test item ID available")
            return False, {}
        return self.run_test("Check Item Price", "POST", f"items/{self.test_item_id}/check", 200)

    def test_get_price_history(self):
        """Test getting price history"""
        if not hasattr(self, 'test_item_id'):
            self.log_test("Get Price History", False, "No test item ID available")
            return False, {}
        return self.run_test("Get Price History", "GET", f"items/{self.test_item_id}/history", 200)

    def test_delete_item(self):
        """Test deleting an item"""
        if not hasattr(self, 'test_item_id'):
            self.log_test("Delete Item", False, "No test item ID available")
            return False, {}
        return self.run_test("Delete Item", "DELETE", f"items/{self.test_item_id}", 200)

    def cleanup_test_data(self):
        """Clean up test data from database"""
        if not self.user_id:
            return
            
        print("\n🧹 Cleaning up test data...")
        
        import subprocess
        
        mongo_cmd = f'''
        use('test_database');
        db.users.deleteMany({{email: /test\\.user\\./}});
        db.user_sessions.deleteMany({{session_token: /test_session/}});
        db.tracked_items.deleteMany({{user_id: "{self.user_id}"}});
        db.price_history.deleteMany({{}});
        '''
        
        try:
            subprocess.run(['mongosh', '--eval', mongo_cmd], timeout=30)
            print("✅ Test data cleaned up")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting PriceSpy API Tests")
        print("=" * 50)
        
        # Test basic endpoints first
        self.test_root_endpoint()
        self.test_auth_me_without_token()
        
        # Create test user and session
        if not self.create_test_user_session():
            print("❌ Cannot continue without test user")
            return False
        
        # Test authenticated endpoints
        self.test_auth_me_with_token()
        self.test_items_list_empty()
        
        # Test preview functionality
        self.test_preview_extraction()
        
        # Test CRUD operations
        self.test_create_item()
        self.test_get_items_with_data()
        self.test_get_item_detail()
        self.test_update_item()
        self.test_check_item_price()
        self.test_get_price_history()
        self.test_delete_item()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed")
            return False

def main():
    tester = PriceSpyAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())