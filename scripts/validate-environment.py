#!/usr/bin/env python3
"""
Environment Validation Script for MBA Job Hunter

This script validates that all required environment variables and services
are properly configured for deployment.
"""

import os
import sys
import asyncio
import asyncpg
import redis
import httpx
from typing import Dict, List, Tuple
import json
from datetime import datetime


class EnvironmentValidator:
    """Validates environment configuration for deployment"""
    
    def __init__(self):
        self.results = []
        self.errors = []
        self.warnings = []
        
    def check_required_env_vars(self) -> bool:
        """Check if all required environment variables are set"""
        required_vars = [
            "SECRET_KEY",
            "DATABASE_URL", 
            "REDIS_URL",
        ]
        
        optional_vars = [
            "OPENAI_API_KEY",
            "NOTION_API_KEY",
            "ANTHROPIC_API_KEY",
            "SENTRY_DSN",
            "SLACK_WEBHOOK_URL"
        ]
        
        print("🔍 Checking environment variables...")
        
        missing_required = []
        missing_optional = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
                self.errors.append(f"Missing required environment variable: {var}")
            else:
                print(f"✅ {var}: Set")
                
        for var in optional_vars:
            if not os.getenv(var):
                missing_optional.append(var)
                self.warnings.append(f"Missing optional environment variable: {var}")
            else:
                print(f"✅ {var}: Set")
                
        if missing_required:
            print(f"❌ Missing required variables: {', '.join(missing_required)}")
            return False
            
        if missing_optional:
            print(f"⚠️  Missing optional variables: {', '.join(missing_optional)}")
            
        return True
    
    async def check_database_connection(self) -> bool:
        """Test database connectivity"""
        print("\n🗃️ Checking database connection...")
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            self.errors.append("DATABASE_URL not set")
            return False
            
        try:
            # Extract connection details
            if database_url.startswith("postgresql+asyncpg://"):
                # Convert to asyncpg format
                db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            else:
                db_url = database_url
                
            conn = await asyncpg.connect(db_url)
            
            # Test basic query
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                print("✅ Database connection successful")
                
                # Check if tables exist
                tables = await conn.fetch("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                
                if tables:
                    print(f"✅ Found {len(tables)} tables in database")
                else:
                    self.warnings.append("No tables found - migrations may be needed")
                    print("⚠️  No tables found - run 'alembic upgrade head'")
                    
            await conn.close()
            return True
            
        except Exception as e:
            self.errors.append(f"Database connection failed: {str(e)}")
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def check_redis_connection(self) -> bool:
        """Test Redis connectivity"""
        print("\n📊 Checking Redis connection...")
        
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            self.errors.append("REDIS_URL not set")
            return False
            
        try:
            r = redis.from_url(redis_url, decode_responses=True)
            
            # Test basic operations
            test_key = "health_check_test"
            r.set(test_key, "test_value", ex=10)
            value = r.get(test_key)
            
            if value == "test_value":
                print("✅ Redis connection successful")
                
                # Get Redis info
                info = r.info()
                print(f"✅ Redis version: {info.get('redis_version', 'unknown')}")
                
                # Cleanup
                r.delete(test_key)
                return True
            else:
                self.errors.append("Redis read/write test failed")
                return False
                
        except Exception as e:
            self.errors.append(f"Redis connection failed: {str(e)}")
            print(f"❌ Redis connection failed: {str(e)}")
            return False
    
    async def check_api_keys(self) -> bool:
        """Test API key validity"""
        print("\n🔑 Checking API keys...")
        
        all_valid = True
        
        # Check OpenAI API Key
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "test_key":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {openai_key}"},
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        print("✅ OpenAI API key is valid")
                    else:
                        self.errors.append(f"OpenAI API key invalid (HTTP {response.status_code})")
                        print(f"❌ OpenAI API key invalid (HTTP {response.status_code})")
                        all_valid = False
            except Exception as e:
                self.warnings.append(f"Could not validate OpenAI API key: {str(e)}")
                print(f"⚠️  Could not validate OpenAI API key: {str(e)}")
        else:
            self.warnings.append("OpenAI API key not set or is test key")
            print("⚠️  OpenAI API key not set")
        
        # Check Notion API Key
        notion_key = os.getenv("NOTION_API_KEY")
        if notion_key and notion_key != "test_key":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.notion.com/v1/users/me",
                        headers={
                            "Authorization": f"Bearer {notion_key}",
                            "Notion-Version": "2022-06-28"
                        },
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        print("✅ Notion API key is valid")
                    else:
                        self.warnings.append(f"Notion API key invalid (HTTP {response.status_code})")
                        print(f"⚠️  Notion API key invalid (HTTP {response.status_code})")
            except Exception as e:
                self.warnings.append(f"Could not validate Notion API key: {str(e)}")
                print(f"⚠️  Could not validate Notion API key: {str(e)}")
        else:
            self.warnings.append("Notion API key not set")
            print("⚠️  Notion API key not set")
        
        return all_valid
    
    def check_security_config(self) -> bool:
        """Check security configuration"""
        print("\n🔒 Checking security configuration...")
        
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key:
            self.errors.append("SECRET_KEY not set")
            return False
        
        if len(secret_key) < 32:
            self.errors.append("SECRET_KEY should be at least 32 characters")
            print("❌ SECRET_KEY too short (minimum 32 characters)")
            return False
        
        if secret_key in ["your-secret-key", "dev-secret-key", "test"]:
            self.errors.append("SECRET_KEY appears to be a default/test value")
            print("❌ SECRET_KEY appears to be default value")
            return False
        
        print("✅ SECRET_KEY is properly configured")
        
        # Check environment
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production":
            debug = os.getenv("DEBUG", "false").lower()
            if debug not in ["false", "0", "no"]:
                self.warnings.append("DEBUG should be disabled in production")
                print("⚠️  DEBUG should be disabled in production")
        
        print(f"✅ Environment: {environment}")
        return True
    
    def generate_report(self) -> Dict:
        """Generate validation report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "passed" if not self.errors else "failed",
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }
    
    async def validate_all(self) -> bool:
        """Run all validation checks"""
        print("🚀 MBA Job Hunter - Environment Validation")
        print("=" * 50)
        
        checks = [
            ("Environment Variables", self.check_required_env_vars()),
            ("Database Connection", await self.check_database_connection()),
            ("Redis Connection", await self.check_redis_connection()),
            ("API Keys", await self.check_api_keys()),
            ("Security Configuration", self.check_security_config())
        ]
        
        all_passed = all(result for name, result in checks)
        
        print("\n" + "=" * 50)
        print("📋 Validation Summary")
        print("=" * 50)
        
        for name, result in checks:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{name}: {status}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        if self.errors:
            print(f"\n❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"   - {error}")
        
        print(f"\nOverall Status: {'✅ PASSED' if all_passed else '❌ FAILED'}")
        
        # Save report
        report = self.generate_report()
        with open("validation-report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Detailed report saved to validation-report.json")
        
        return all_passed


async def main():
    """Main validation function"""
    validator = EnvironmentValidator()
    
    try:
        success = await validator.validate_all()
        
        if success:
            print("\n🎉 Environment validation completed successfully!")
            print("Your environment is ready for deployment.")
            sys.exit(0)
        else:
            print("\n❌ Environment validation failed!")
            print("Please fix the errors above before deploying.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if required packages are available
    try:
        import asyncpg
        import redis
        import httpx
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install required packages:")
        print("pip install asyncpg redis httpx")
        sys.exit(1)
    
    asyncio.run(main())