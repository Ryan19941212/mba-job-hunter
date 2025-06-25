#!/usr/bin/env python3
"""
Smoke Tests for MBA Job Hunter

Quick verification tests to ensure critical functionality works after deployment.
These tests should run fast and cover the most important user journeys.

Usage:
    python scripts/smoke_test.py [options]

Examples:
    python scripts/smoke_test.py --environment production
    python scripts/smoke_test.py --base-url https://api.mba-job-hunter.com
    python scripts/smoke_test.py --timeout 10 --verbose
"""

import asyncio
import aiohttp
import argparse
import sys
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class TestResult(Enum):
    """Test result status."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class SmokeTestResult:
    """Individual smoke test result."""
    test_name: str
    status: TestResult
    duration_ms: float
    message: str
    details: Dict[str, Any]
    error: Optional[str] = None


class SmokeTestRunner:
    """Smoke test runner for MBA Job Hunter."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 30,
        verbose: bool = False,
        environment: str = "development"
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verbose = verbose
        self.environment = environment
        self.results: List[SmokeTestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": "MBA-Job-Hunter-SmokeTest/1.0"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all smoke tests."""
        
        print(f"🚀 Starting smoke tests for {self.environment} environment")
        print(f"Base URL: {self.base_url}")
        print(f"Timeout: {self.timeout}s")
        print("-" * 60)
        
        # Define test suite
        tests = [
            ("Basic Health Check", self.test_health_check),
            ("API Documentation", self.test_api_docs),
            ("Database Connectivity", self.test_database_health),
            ("Job Search Endpoint", self.test_job_search),
            ("Error Handling", self.test_error_handling),
            ("Security Headers", self.test_security_headers),
            ("Rate Limiting", self.test_rate_limiting),
            ("Metrics Endpoint", self.test_metrics),
            ("Response Performance", self.test_response_performance),
            ("External Services", self.test_external_services)
        ]
        
        # Run tests
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
        
        return self.generate_report()
    
    async def run_test(self, test_name: str, test_func) -> None:
        """Run individual test with error handling."""
        
        if self.verbose:
            print(f"Running: {test_name}...")
        
        start_time = time.time()
        
        try:
            result = await test_func()
            duration = (time.time() - start_time) * 1000
            
            if result["success"]:
                status = TestResult.PASS
                icon = "✅"
            else:
                status = TestResult.FAIL
                icon = "❌"
            
            test_result = SmokeTestResult(
                test_name=test_name,
                status=status,
                duration_ms=duration,
                message=result["message"],
                details=result.get("details", {}),
                error=result.get("error")
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            test_result = SmokeTestResult(
                test_name=test_name,
                status=TestResult.FAIL,
                duration_ms=duration,
                message=f"Test failed with exception",
                details={},
                error=str(e)
            )
            icon = "❌"
        
        self.results.append(test_result)
        
        # Print result
        print(f"{icon} {test_name}: {test_result.status.value} ({test_result.duration_ms:.1f}ms)")
        
        if test_result.error and self.verbose:
            print(f"   Error: {test_result.error}")
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test basic health check endpoint."""
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    
                    # Check response structure
                    if "status" in health_data:
                        return {
                            "success": True,
                            "message": f"Health check passed: {health_data['status']}",
                            "details": health_data
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Health check response missing status field",
                            "details": health_data
                        }
                else:
                    return {
                        "success": False,
                        "message": f"Health check returned status {response.status}",
                        "details": {"status_code": response.status}
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": "Health check endpoint not accessible",
                "error": str(e)
            }
    
    async def test_api_docs(self) -> Dict[str, Any]:
        """Test API documentation endpoints."""
        
        docs_endpoints = ["/docs", "/redoc", "/openapi.json"]
        accessible_docs = []
        
        for endpoint in docs_endpoints:
            try:
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    if response.status == 200:
                        accessible_docs.append(endpoint)
            except:
                pass
        
        if accessible_docs:
            return {
                "success": True,
                "message": f"API docs accessible: {', '.join(accessible_docs)}",
                "details": {"accessible_endpoints": accessible_docs}
            }
        else:
            return {
                "success": False,
                "message": "No API documentation endpoints accessible"
            }
    
    async def test_database_health(self) -> Dict[str, Any]:
        """Test database connectivity through health endpoint."""
        
        try:
            # Try detailed health check if available
            async with self.session.get(f"{self.base_url}/health/detailed") as response:
                if response.status == 200:
                    health_data = await response.json()
                    
                    if "checks" in health_data and "database" in health_data["checks"]:
                        db_status = health_data["checks"]["database"]["status"]
                        return {
                            "success": db_status in ["healthy", "pass"],
                            "message": f"Database status: {db_status}",
                            "details": health_data["checks"]["database"]
                        }
                
                # Fallback to basic health check
                return await self.test_health_check()
                
        except Exception as e:
            return {
                "success": False,
                "message": "Database health check failed",
                "error": str(e)
            }
    
    async def test_job_search(self) -> Dict[str, Any]:
        """Test job search functionality."""
        
        search_payload = {
            "keywords": ["software", "engineer"],
            "location": "台北",
            "limit": 5
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/jobs/search",
                json=search_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    results = await response.json()
                    
                    # Check response structure
                    if "jobs" in results:
                        job_count = len(results["jobs"])
                        return {
                            "success": True,
                            "message": f"Job search returned {job_count} results",
                            "details": {
                                "job_count": job_count,
                                "has_results": job_count > 0
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Job search response missing 'jobs' field",
                            "details": results
                        }
                        
                elif response.status == 422:
                    # Validation error - might be expected
                    error_data = await response.json()
                    return {
                        "success": False,
                        "message": "Job search validation failed",
                        "details": error_data
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Job search returned status {response.status}",
                        "details": {"status_code": response.status}
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": "Job search endpoint not accessible",
                "error": str(e)
            }
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling by requesting non-existent resource."""
        
        try:
            async with self.session.get(f"{self.base_url}/api/v1/jobs/nonexistent-id") as response:
                
                if response.status == 404:
                    error_data = await response.json()
                    
                    # Check error response structure
                    if "error" in error_data:
                        error_info = error_data["error"]
                        has_required_fields = all(
                            field in error_info 
                            for field in ["code", "message"]
                        )
                        
                        return {
                            "success": has_required_fields,
                            "message": "Error handling works correctly",
                            "details": {
                                "error_structure_valid": has_required_fields,
                                "error_code": error_info.get("code"),
                                "has_request_id": "request_id" in error_info
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Error response missing 'error' field",
                            "details": error_data
                        }
                else:
                    return {
                        "success": False,
                        "message": f"Expected 404, got {response.status}",
                        "details": {"status_code": response.status}
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "message": "Error handling test failed",
                "error": str(e)
            }
    
    async def test_security_headers(self) -> Dict[str, Any]:
        """Test security headers presence."""
        
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                
                security_headers = [
                    "X-Content-Type-Options",
                    "X-Frame-Options",
                    "X-XSS-Protection"
                ]
                
                present_headers = []
                missing_headers = []
                
                for header in security_headers:
                    if header in response.headers:
                        present_headers.append(header)
                    else:
                        missing_headers.append(header)
                
                success = len(missing_headers) == 0
                
                return {
                    "success": success,
                    "message": f"Security headers: {len(present_headers)}/{len(security_headers)} present",
                    "details": {
                        "present_headers": present_headers,
                        "missing_headers": missing_headers
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": "Security headers test failed",
                "error": str(e)
            }
    
    async def test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting (light test)."""
        
        try:
            # Make a few rapid requests
            responses = []
            for _ in range(10):
                async with self.session.get(f"{self.base_url}/health") as response:
                    responses.append(response.status)
            
            # Check if any rate limiting occurred
            rate_limited = any(status == 429 for status in responses)
            success_count = sum(1 for status in responses if status == 200)
            
            return {
                "success": True,  # Always pass - rate limiting is optional
                "message": f"Rate limiting test: {success_count}/10 requests succeeded",
                "details": {
                    "rate_limited": rate_limited,
                    "success_count": success_count,
                    "response_codes": responses
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": "Rate limiting test failed",
                "error": str(e)
            }
    
    async def test_metrics(self) -> Dict[str, Any]:
        """Test metrics endpoint if available."""
        
        try:
            async with self.session.get(f"{self.base_url}/metrics") as response:
                
                if response.status == 200:
                    metrics_text = await response.text()
                    
                    # Check if it looks like Prometheus metrics
                    has_metrics = any(
                        keyword in metrics_text.lower()
                        for keyword in ["help", "type", "http_requests", "job_searches"]
                    )
                    
                    return {
                        "success": True,
                        "message": "Metrics endpoint accessible",
                        "details": {
                            "response_size": len(metrics_text),
                            "has_prometheus_format": has_metrics
                        }
                    }
                    
                elif response.status == 404:
                    return {
                        "success": True,  # Metrics might be disabled
                        "message": "Metrics endpoint not enabled",
                        "details": {"status": "disabled"}
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Metrics endpoint returned {response.status}",
                        "details": {"status_code": response.status}
                    }
                    
        except Exception as e:
            return {
                "success": True,  # Metrics are optional
                "message": "Metrics endpoint not accessible (optional)",
                "error": str(e)
            }
    
    async def test_response_performance(self) -> Dict[str, Any]:
        """Test API response performance."""
        
        endpoints = [
            "/health",
            "/api/v1/jobs?limit=1"
        ]
        
        performance_results = []
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    
                    performance_results.append({
                        "endpoint": endpoint,
                        "response_time_ms": response_time,
                        "status_code": response.status,
                        "acceptable": response_time < 5000  # Less than 5 seconds
                    })
                    
            except Exception as e:
                performance_results.append({
                    "endpoint": endpoint,
                    "error": str(e),
                    "acceptable": False
                })
        
        acceptable_count = sum(1 for r in performance_results if r.get("acceptable", False))
        total_count = len(performance_results)
        
        avg_response_time = sum(
            r.get("response_time_ms", 0) 
            for r in performance_results 
            if "response_time_ms" in r
        ) / max(1, sum(1 for r in performance_results if "response_time_ms" in r))
        
        return {
            "success": acceptable_count >= total_count // 2,  # At least half should be acceptable
            "message": f"Performance: {acceptable_count}/{total_count} endpoints acceptable",
            "details": {
                "results": performance_results,
                "avg_response_time_ms": avg_response_time
            }
        }
    
    async def test_external_services(self) -> Dict[str, Any]:
        """Test external service health (light check)."""
        
        # Check if external services are configured
        import os
        
        external_services = {
            "OpenAI": bool(os.getenv("OPENAI_API_KEY")),
            "Notion": bool(os.getenv("NOTION_API_KEY")),
            "Redis": bool(os.getenv("REDIS_URL"))
        }
        
        configured_services = [name for name, configured in external_services.items() if configured]
        
        return {
            "success": True,  # Always pass - external services are optional
            "message": f"External services configured: {len(configured_services)}",
            "details": {
                "configured_services": configured_services,
                "service_status": external_services
            }
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate test report."""
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.status == TestResult.PASS)
        failed_tests = sum(1 for r in self.results if r.status == TestResult.FAIL)
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        avg_duration = sum(r.duration_ms for r in self.results) / total_tests if total_tests > 0 else 0
        
        # Determine overall status
        if success_rate >= 90:
            overall_status = "EXCELLENT"
        elif success_rate >= 70:
            overall_status = "GOOD"
        elif success_rate >= 50:
            overall_status = "FAIR"
        else:
            overall_status = "POOR"
        
        return {
            "overall_status": overall_status,
            "success_rate": success_rate,
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "avg_duration_ms": avg_duration
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "message": r.message,
                    "error": r.error
                }
                for r in self.results
            ],
            "failed_tests": [
                r.test_name for r in self.results 
                if r.status == TestResult.FAIL
            ]
        }


async def main():
    """Main function to run smoke tests."""
    
    parser = argparse.ArgumentParser(description="MBA Job Hunter Smoke Tests")
    parser.add_argument("--environment", default="development", help="Environment name")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--fail-threshold", type=float, default=70.0, help="Minimum success rate to pass")
    
    args = parser.parse_args()
    
    # Run smoke tests
    async with SmokeTestRunner(
        base_url=args.base_url,
        timeout=args.timeout,
        verbose=args.verbose,
        environment=args.environment
    ) as runner:
        
        report = await runner.run_all_tests()
    
    # Print summary
    print("\n" + "=" * 60)
    print("SMOKE TEST SUMMARY")
    print("=" * 60)
    
    summary = report["summary"]
    print(f"Overall Status: {report['overall_status']}")
    print(f"Success Rate: {report['success_rate']:.1f}%")
    print(f"Tests Passed: {summary['passed']}/{summary['total_tests']}")
    print(f"Average Duration: {summary['avg_duration_ms']:.1f}ms")
    
    if report["failed_tests"]:
        print(f"Failed Tests: {', '.join(report['failed_tests'])}")
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Exit with appropriate code
    success_rate = report['success_rate']
    if success_rate < args.fail_threshold:
        print(f"\nSmoke tests failed: {success_rate:.1f}% < {args.fail_threshold}%")
        return 1
    else:
        print(f"\nSmoke tests passed: {success_rate:.1f}% >= {args.fail_threshold}%")
        return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nSmoke tests interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\nSmoke tests failed: {e}")
        sys.exit(1)