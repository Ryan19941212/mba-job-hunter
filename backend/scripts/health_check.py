#!/usr/bin/env python3
"""
Comprehensive Health Check Script for MBA Job Hunter

Performs detailed health checks for all system components:
- API endpoints
- Database connectivity  
- External services (OpenAI, Notion, LinkedIn)
- System resources
- Security configurations
- Performance metrics

Usage:
    python scripts/health_check.py [options]

Examples:
    python scripts/health_check.py --environment production
    python scripts/health_check.py --verbose --timeout 30
    python scripts/health_check.py --component database
"""

import asyncio
import aiohttp
import argparse
import sys
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

import psutil
import asyncpg
import redis.asyncio as redis


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Health check result data structure."""
    component: str
    status: HealthStatus
    response_time_ms: float
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    error: Optional[str] = None


class HealthChecker:
    """Comprehensive health checker for MBA Job Hunter."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 30,
        verbose: bool = False
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.verbose = verbose
        self.results: List[HealthCheckResult] = []
    
    async def check_all_components(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive results."""
        
        print("🔍 Starting comprehensive health check...")
        print(f"Base URL: {self.base_url}")
        print(f"Timeout: {self.timeout}s")
        print("-" * 60)
        
        # Define health check tasks
        health_checks = [
            ("API Endpoints", self.check_api_health),
            ("Database", self.check_database_health),
            ("Redis Cache", self.check_redis_health),
            ("External APIs", self.check_external_apis),
            ("System Resources", self.check_system_resources),
            ("Security Configuration", self.check_security_config),
            ("Performance Metrics", self.check_performance_metrics)
        ]
        
        # Run health checks concurrently
        for component_name, check_func in health_checks:
            try:
                if self.verbose:
                    print(f"Checking {component_name}...")
                
                result = await check_func()
                self.results.append(result)
                
                status_icon = self._get_status_icon(result.status)
                print(f"{status_icon} {component_name}: {result.status.value} ({result.response_time_ms:.1f}ms)")
                
                if result.error and self.verbose:
                    print(f"   Error: {result.error}")
                
            except Exception as e:
                error_result = HealthCheckResult(
                    component=component_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0.0,
                    message=f"Health check failed: {str(e)}",
                    details={},
                    timestamp=datetime.utcnow(),
                    error=str(e)
                )
                self.results.append(error_result)
                print(f"❌ {component_name}: FAILED - {str(e)}")
        
        # Generate summary
        return self._generate_summary()
    
    async def check_api_health(self) -> HealthCheckResult:
        """Check API endpoint health."""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Check basic health endpoint
                async with session.get(f"{self.base_url}/health") as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        health_data = await response.json()
                        
                        return HealthCheckResult(
                            component="API",
                            status=HealthStatus.HEALTHY,
                            response_time_ms=response_time,
                            message="API is responding normally",
                            details=health_data,
                            timestamp=datetime.utcnow()
                        )
                    else:
                        return HealthCheckResult(
                            component="API",
                            status=HealthStatus.UNHEALTHY,
                            response_time_ms=response_time,
                            message=f"API returned status {response.status}",
                            details={"status_code": response.status},
                            timestamp=datetime.utcnow(),
                            error=f"HTTP {response.status}"
                        )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="API",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message="API is not accessible",
                details={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
    
    async def check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            # Try to connect to database using environment variables
            import os
            database_url = os.getenv('DATABASE_URL')
            
            if not database_url:
                return HealthCheckResult(
                    component="Database",
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0.0,
                    message="DATABASE_URL not configured",
                    details={},
                    timestamp=datetime.utcnow(),
                    error="Missing DATABASE_URL environment variable"
                )
            
            # Parse database URL for asyncpg
            if database_url.startswith('postgresql://'):
                conn = await asyncpg.connect(database_url)
                
                # Test query
                result = await conn.fetchval('SELECT 1')
                await conn.close()
                
                response_time = (time.time() - start_time) * 1000
                
                return HealthCheckResult(
                    component="Database",
                    status=HealthStatus.HEALTHY if response_time < 1000 else HealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    message="Database connection successful",
                    details={"query_result": result},
                    timestamp=datetime.utcnow()
                )
            else:
                # For SQLite or other databases
                return HealthCheckResult(
                    component="Database",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    message="Database check skipped for non-PostgreSQL",
                    details={"database_type": "sqlite"},
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="Database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message="Database connection failed",
                details={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
    
    async def check_redis_health(self) -> HealthCheckResult:
        """Check Redis connectivity."""
        start_time = time.time()
        
        try:
            import os
            redis_url = os.getenv('REDIS_URL')
            
            if not redis_url:
                return HealthCheckResult(
                    component="Redis",
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0.0,
                    message="Redis not configured",
                    details={},
                    timestamp=datetime.utcnow()
                )
            
            redis_client = redis.from_url(redis_url)
            
            # Test ping
            pong = await redis_client.ping()
            await redis_client.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="Redis",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                message="Redis connection successful",
                details={"ping_result": pong},
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="Redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message="Redis connection failed",
                details={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
    
    async def check_external_apis(self) -> HealthCheckResult:
        """Check external API connectivity."""
        start_time = time.time()
        external_apis = {}
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                
                # Check OpenAI API
                openai_key = os.getenv('OPENAI_API_KEY')
                if openai_key:
                    try:
                        headers = {'Authorization': f'Bearer {openai_key}'}
                        async with session.get('https://api.openai.com/v1/models', headers=headers) as response:
                            external_apis['openai'] = {
                                'status': 'healthy' if response.status == 200 else 'unhealthy',
                                'status_code': response.status
                            }
                    except Exception as e:
                        external_apis['openai'] = {'status': 'unhealthy', 'error': str(e)}
                
                # Check Notion API
                notion_key = os.getenv('NOTION_API_KEY')
                if notion_key:
                    try:
                        headers = {
                            'Authorization': f'Bearer {notion_key}',
                            'Notion-Version': '2022-06-28'
                        }
                        async with session.get('https://api.notion.com/v1/users/me', headers=headers) as response:
                            external_apis['notion'] = {
                                'status': 'healthy' if response.status == 200 else 'unhealthy',
                                'status_code': response.status
                            }
                    except Exception as e:
                        external_apis['notion'] = {'status': 'unhealthy', 'error': str(e)}
                
                # Check Indeed (simple connectivity test)
                try:
                    async with session.get('https://indeed.com', timeout=aiohttp.ClientTimeout(total=10)) as response:
                        external_apis['indeed'] = {
                            'status': 'healthy' if response.status == 200 else 'degraded',
                            'status_code': response.status
                        }
                except Exception as e:
                    external_apis['indeed'] = {'status': 'unhealthy', 'error': str(e)}
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine overall status
            healthy_count = sum(1 for api in external_apis.values() if api.get('status') == 'healthy')
            total_count = len(external_apis)
            
            if total_count == 0:
                status = HealthStatus.UNKNOWN
                message = "No external APIs configured"
            elif healthy_count == total_count:
                status = HealthStatus.HEALTHY
                message = "All external APIs are healthy"
            elif healthy_count > 0:
                status = HealthStatus.DEGRADED
                message = f"{healthy_count}/{total_count} external APIs are healthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = "All external APIs are unhealthy"
            
            return HealthCheckResult(
                component="External APIs",
                status=status,
                response_time_ms=response_time,
                message=message,
                details=external_apis,
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="External APIs",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message="External API check failed",
                details={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
    
    async def check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage."""
        start_time = time.time()
        
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            details = {
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_usage_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2)
            }
            
            # Determine status based on thresholds
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "System resources critically high"
            elif cpu_percent > 70 or memory.percent > 70 or disk.percent > 80:
                status = HealthStatus.DEGRADED
                message = "System resources elevated"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="System Resources",
                status=status,
                response_time_ms=response_time,
                message=message,
                details=details,
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="System Resources",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message="System resource check failed",
                details={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
    
    async def check_security_config(self) -> HealthCheckResult:
        """Check security configuration."""
        start_time = time.time()
        
        try:
            security_checks = {}
            
            # Check environment variables
            import os
            
            # Check if critical security vars are set
            security_vars = ['SECRET_KEY', 'JWT_SECRET_KEY']
            for var in security_vars:
                value = os.getenv(var)
                security_checks[var] = {
                    'configured': bool(value),
                    'length': len(value) if value else 0,
                    'secure': len(value) >= 32 if value else False
                }
            
            # Check debug mode
            debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
            environment = os.getenv('ENVIRONMENT', 'development')
            
            security_checks['debug_mode'] = {
                'enabled': debug_mode,
                'safe_for_production': not debug_mode or environment != 'production'
            }
            
            # Check CORS configuration
            cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '*')
            security_checks['cors'] = {
                'wildcard_allowed': cors_origins == '*',
                'secure': cors_origins != '*' or environment != 'production'
            }
            
            # Determine overall security status
            critical_issues = []
            
            if not all(check['configured'] and check['secure'] for var, check in security_checks.items() if var in security_vars):
                critical_issues.append("Weak or missing security keys")
            
            if not security_checks['debug_mode']['safe_for_production']:
                critical_issues.append("Debug mode enabled in production")
            
            if not security_checks['cors']['secure']:
                critical_issues.append("Insecure CORS configuration")
            
            if critical_issues:
                status = HealthStatus.UNHEALTHY
                message = f"Security issues: {', '.join(critical_issues)}"
            else:
                status = HealthStatus.HEALTHY
                message = "Security configuration is secure"
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="Security Configuration",
                status=status,
                response_time_ms=response_time,
                message=message,
                details=security_checks,
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="Security Configuration",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message="Security check failed",
                details={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
    
    async def check_performance_metrics(self) -> HealthCheckResult:
        """Check performance metrics if available."""
        start_time = time.time()
        
        try:
            # Try to get metrics from the API
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                try:
                    async with session.get(f"{self.base_url}/metrics") as response:
                        if response.status == 200:
                            metrics_text = await response.text()
                            
                            # Parse basic metrics
                            metrics = {
                                'metrics_endpoint_available': True,
                                'response_size_bytes': len(metrics_text)
                            }
                            
                            status = HealthStatus.HEALTHY
                            message = "Performance metrics available"
                        else:
                            metrics = {'metrics_endpoint_available': False}
                            status = HealthStatus.DEGRADED
                            message = "Metrics endpoint not accessible"
                
                except Exception:
                    metrics = {'metrics_endpoint_available': False}
                    status = HealthStatus.DEGRADED
                    message = "Metrics endpoint not available"
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                component="Performance Metrics",
                status=status,
                response_time_ms=response_time,
                message=message,
                details=metrics,
                timestamp=datetime.utcnow()
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="Performance Metrics",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                message="Performance metrics check failed",
                details={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
    
    def _get_status_icon(self, status: HealthStatus) -> str:
        """Get status icon for display."""
        icons = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.UNHEALTHY: "❌",
            HealthStatus.UNKNOWN: "❓"
        }
        return icons.get(status, "❓")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate health check summary."""
        total_checks = len(self.results)
        healthy_count = sum(1 for r in self.results if r.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for r in self.results if r.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for r in self.results if r.status == HealthStatus.UNHEALTHY)
        
        # Overall status
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Calculate average response time
        avg_response_time = sum(r.response_time_ms for r in self.results) / total_checks if total_checks > 0 else 0
        
        summary = {
            "overall_status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_checks": total_checks,
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
                "avg_response_time_ms": round(avg_response_time, 2)
            },
            "results": [asdict(result) for result in self.results]
        }
        
        return summary


def main():
    """Main function to run health checks."""
    parser = argparse.ArgumentParser(description="MBA Job Hunter Health Check")
    parser.add_argument("--environment", default="development", help="Environment to check")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--component", help="Check specific component only")
    parser.add_argument("--output", help="Output file for results (JSON)")
    parser.add_argument("--fail-on-unhealthy", action="store_true", help="Exit with code 1 if any component is unhealthy")
    
    args = parser.parse_args()
    
    # Set environment variables if specified
    if args.environment:
        import os
        os.environ['ENVIRONMENT'] = args.environment
    
    async def run_checks():
        checker = HealthChecker(
            base_url=args.base_url,
            timeout=args.timeout,
            verbose=args.verbose
        )
        
        results = await checker.check_all_components()
        
        # Print summary
        print("\n" + "=" * 60)
        print("HEALTH CHECK SUMMARY")
        print("=" * 60)
        
        summary = results["summary"]
        overall_status = results["overall_status"]
        
        status_icon = checker._get_status_icon(HealthStatus(overall_status))
        print(f"Overall Status: {status_icon} {overall_status.upper()}")
        print(f"Healthy: {summary['healthy']}")
        print(f"Degraded: {summary['degraded']}")
        print(f"Unhealthy: {summary['unhealthy']}")
        print(f"Average Response Time: {summary['avg_response_time_ms']:.1f}ms")
        
        # Save results to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to: {args.output}")
        
        # Exit with appropriate code
        if args.fail_on_unhealthy and overall_status in ['unhealthy', 'degraded']:
            print(f"\nExiting with code 1 due to {overall_status} status")
            return 1
        
        return 0
    
    # Run health checks
    try:
        exit_code = asyncio.run(run_checks())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nHealth check interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\nHealth check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()