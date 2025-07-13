#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Truth Detector API
Tests all endpoints and core functionality
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

class TruthDetectorAPITester:
    def __init__(self, base_url: str = "https://60200931-6508-419f-8406-421178946019.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - {details}")
        
        self.test_results.append({
            'name': name,
            'success': success,
            'details': details,
            'response_data': response_data
        })

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Dict = None, headers: Dict = None) -> tuple:
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                self.log_test(name, False, f"Unsupported method: {method}")
                return False, {}

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            if success:
                self.log_test(name, True, f"Status: {response.status_code}", response_data)
            else:
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}", response_data)

            return success, response_data

        except requests.exceptions.Timeout:
            self.log_test(name, False, "Request timeout")
            return False, {}
        except requests.exceptions.ConnectionError:
            self.log_test(name, False, "Connection error")
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return False, {}

    def test_health_endpoint(self):
        """Test health check endpoint"""
        print("\n🔍 Testing Health Endpoint...")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        
        if success and response:
            # Validate response structure
            required_fields = ['status', 'timestamp', 'service']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log_test("Health Response Structure", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Health Response Structure", True, "All required fields present")
        
        return success

    def test_truth_demo_endpoint(self):
        """Test truth demo endpoint"""
        print("\n🔍 Testing Truth Demo Endpoint...")
        success, response = self.run_test(
            "Truth Demo",
            "POST",
            "truth-demo",
            200
        )
        
        if success and response:
            # Validate demo response structure
            required_fields = ['message', 'demo_claims_count', 'results']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log_test("Demo Response Structure", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Demo Response Structure", True, "All required fields present")
                
                # Validate results structure
                results = response.get('results', {})
                result_fields = ['total_claims', 'total_clusters', 'contradictions', 'probable_truths', 'inconsistencies', 'narrative', 'summary']
                missing_result_fields = [field for field in result_fields if field not in results]
                if missing_result_fields:
                    self.log_test("Demo Results Structure", False, f"Missing result fields: {missing_result_fields}")
                else:
                    self.log_test("Demo Results Structure", True, "All result fields present")
        
        return success, response

    def test_truth_analyze_custom_claims(self):
        """Test truth analyze endpoint with custom claims"""
        print("\n🔍 Testing Truth Analyze with Custom Claims...")
        
        # Test with valid claims
        test_claims = {
            "claims": [
                {"text": "The Earth is round", "source_type": "science"},
                {"text": "The Earth is flat", "source_type": "conspiracy"},
                {"text": "Water boils at 100°C", "source_type": "science"},
                {"text": "Exercise is good for health", "source_type": "health"}
            ]
        }
        
        success, response = self.run_test(
            "Truth Analyze - Valid Claims",
            "POST",
            "truth-analyze",
            200,
            test_claims
        )
        
        analysis_id = None
        if success and response:
            # Validate response structure
            required_fields = ['id', 'timestamp', 'total_claims', 'total_clusters', 'contradictions', 
                             'probable_truths', 'inconsistencies', 'narrative', 'summary', 'clusters']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                self.log_test("Analyze Response Structure", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Analyze Response Structure", True, "All required fields present")
                analysis_id = response.get('id')
        
        return success, analysis_id

    def test_truth_analyze_edge_cases(self):
        """Test truth analyze endpoint with edge cases"""
        print("\n🔍 Testing Truth Analyze Edge Cases...")
        
        # Test with empty claims
        empty_claims = {"claims": []}
        success, _ = self.run_test(
            "Truth Analyze - Empty Claims",
            "POST",
            "truth-analyze",
            422  # Validation error expected
        )
        
        # Test with invalid claim structure
        invalid_claims = {"claims": [{"invalid_field": "test"}]}
        success, _ = self.run_test(
            "Truth Analyze - Invalid Structure",
            "POST",
            "truth-analyze",
            422  # Validation error expected
        )
        
        # Test with very long claim
        long_claim = {"claims": [{"text": "x" * 3000, "source_type": "test"}]}
        success, _ = self.run_test(
            "Truth Analyze - Long Claim",
            "POST",
            "truth-analyze",
            422  # Should fail validation
        )
        
        # Test with single claim
        single_claim = {"claims": [{"text": "Single test claim", "source_type": "test"}]}
        success, _ = self.run_test(
            "Truth Analyze - Single Claim",
            "POST",
            "truth-analyze",
            200
        )

    def test_contradiction_detection(self):
        """Test contradiction detection specifically"""
        print("\n🔍 Testing Contradiction Detection...")
        
        contradictory_claims = {
            "claims": [
                {"text": "The sky is blue during the day", "source_type": "observation"},
                {"text": "The sky is green during the day", "source_type": "false_claim"},
                {"text": "Water freezes at 0°C", "source_type": "science"},
                {"text": "Water freezes at 50°C", "source_type": "false_claim"},
                {"text": "Humans need oxygen to breathe", "source_type": "biology"},
                {"text": "Humans don't need oxygen to breathe", "source_type": "false_claim"}
            ]
        }
        
        success, response = self.run_test(
            "Contradiction Detection",
            "POST",
            "truth-analyze",
            200,
            contradictory_claims
        )
        
        if success and response:
            contradictions = response.get('contradictions', 0)
            inconsistencies = response.get('inconsistencies', [])
            
            if contradictions > 0:
                self.log_test("Contradictions Detected", True, f"Found {contradictions} contradictions")
            else:
                self.log_test("Contradictions Detected", False, "No contradictions detected in obviously contradictory claims")
            
            if len(inconsistencies) > 0:
                self.log_test("Inconsistencies Listed", True, f"Found {len(inconsistencies)} inconsistencies")
            else:
                self.log_test("Inconsistencies Listed", False, "No inconsistencies listed")

    def test_get_analysis_by_id(self, analysis_id: str):
        """Test getting analysis by ID"""
        if not analysis_id:
            self.log_test("Get Analysis by ID", False, "No analysis ID provided")
            return
            
        print(f"\n🔍 Testing Get Analysis by ID: {analysis_id}...")
        
        success, response = self.run_test(
            "Get Analysis by ID",
            "GET",
            f"truth-analyze/{analysis_id}",
            200
        )
        
        if success and response:
            # Validate that we got the same analysis
            if response.get('id') == analysis_id:
                self.log_test("Analysis ID Match", True, "Retrieved correct analysis")
            else:
                self.log_test("Analysis ID Match", False, f"Expected ID {analysis_id}, got {response.get('id')}")

    def test_get_nonexistent_analysis(self):
        """Test getting non-existent analysis"""
        print("\n🔍 Testing Get Non-existent Analysis...")
        
        fake_id = "non-existent-id-12345"
        success, response = self.run_test(
            "Get Non-existent Analysis",
            "GET",
            f"truth-analyze/{fake_id}",
            404
        )

    def test_list_analyses(self):
        """Test listing analyses"""
        print("\n🔍 Testing List Analyses...")
        
        success, response = self.run_test(
            "List Analyses",
            "GET",
            "truth-analyze",
            200
        )
        
        if success and response:
            if isinstance(response, list):
                self.log_test("List Response Type", True, f"Got list with {len(response)} items")
            else:
                self.log_test("List Response Type", False, f"Expected list, got {type(response)}")

    def test_clustering_algorithm(self):
        """Test clustering with similar claims"""
        print("\n🔍 Testing Clustering Algorithm...")
        
        similar_claims = {
            "claims": [
                {"text": "Exercise improves cardiovascular health", "source_type": "medical"},
                {"text": "Physical activity is good for the heart", "source_type": "health"},
                {"text": "Working out strengthens the cardiovascular system", "source_type": "fitness"},
                {"text": "The Earth orbits around the Sun", "source_type": "astronomy"},
                {"text": "Our planet revolves around the solar system's star", "source_type": "science"},
                {"text": "Eating vegetables provides essential nutrients", "source_type": "nutrition"},
                {"text": "Consuming plant foods gives important vitamins", "source_type": "dietary"}
            ]
        }
        
        success, response = self.run_test(
            "Clustering Algorithm",
            "POST",
            "truth-analyze",
            200,
            similar_claims
        )
        
        if success and response:
            total_claims = response.get('total_claims', 0)
            total_clusters = response.get('total_clusters', 0)
            
            # Should cluster similar claims together
            if total_clusters < total_claims:
                self.log_test("Clustering Effectiveness", True, f"Clustered {total_claims} claims into {total_clusters} clusters")
            else:
                self.log_test("Clustering Effectiveness", False, f"No clustering occurred: {total_claims} claims, {total_clusters} clusters")

    def test_source_diversity_weighting(self):
        """Test source diversity weighting"""
        print("\n🔍 Testing Source Diversity Weighting...")
        
        diverse_sources = {
            "claims": [
                {"text": "Climate change is caused by human activities", "source_type": "science"},
                {"text": "Climate change is caused by human activities", "source_type": "government"},
                {"text": "Climate change is caused by human activities", "source_type": "academic"},
                {"text": "Climate change is caused by human activities", "source_type": "expert"},
                {"text": "Climate change is natural", "source_type": "opinion"}
            ]
        }
        
        success, response = self.run_test(
            "Source Diversity Weighting",
            "POST",
            "truth-analyze",
            200,
            diverse_sources
        )
        
        if success and response:
            probable_truths = response.get('probable_truths', [])
            if probable_truths:
                # Check if the claim with more diverse sources has higher support
                for truth in probable_truths:
                    if truth.get('sources', 0) > 1:
                        self.log_test("Source Diversity Impact", True, f"Found truth with {truth['sources']} sources")
                        break
                else:
                    self.log_test("Source Diversity Impact", False, "No truths with multiple sources found")

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Comprehensive Truth Detector API Testing...")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Basic endpoint tests
        self.test_health_endpoint()
        demo_success, demo_response = self.test_truth_demo_endpoint()
        
        # Custom analysis tests
        analyze_success, analysis_id = self.test_truth_analyze_custom_claims()
        self.test_truth_analyze_edge_cases()
        
        # Advanced algorithm tests
        self.test_contradiction_detection()
        self.test_clustering_algorithm()
        self.test_source_diversity_weighting()
        
        # Analysis retrieval tests
        if analysis_id:
            self.test_get_analysis_by_id(analysis_id)
        self.test_get_nonexistent_analysis()
        self.test_list_analyses()
        
        # Print final results
        self.print_final_results()

    def print_final_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 60)
        print("📊 FINAL TEST RESULTS")
        print("=" * 60)
        
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        # Show failed tests
        failed_tests = [test for test in self.test_results if not test['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        # Show successful critical tests
        critical_tests = ['Health Check', 'Truth Demo', 'Truth Analyze - Valid Claims', 'Contradiction Detection']
        critical_passed = [test for test in self.test_results if test['name'] in critical_tests and test['success']]
        print(f"\n✅ CRITICAL TESTS PASSED ({len(critical_passed)}/{len(critical_tests)}):")
        for test in critical_passed:
            print(f"  - {test['name']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = TruthDetectorAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n💥 Critical testing error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())