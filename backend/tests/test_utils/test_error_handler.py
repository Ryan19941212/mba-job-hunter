"""
Test cases for the UserFriendlyErrorHandler system.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.utils.error_handler import (
    UserFriendlyErrorHandler,
    ErrorContext,
    ApplicationError,
    handle_intelligent_error
)


class TestUserFriendlyErrorHandler:
    """Test the UserFriendlyErrorHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = UserFriendlyErrorHandler()
        self.context = ErrorContext(
            user_id="test_user_123",
            request_id="req_456",
            endpoint="/api/v1/jobs",
            method="GET"
        )
    
    def test_error_mappings_exist(self):
        """Test that all required error mappings are defined."""
        required_errors = [
            'linkedin_rate_limit',
            'notion_api_error', 
            'openai_quota_exceeded',
            'indeed_scraping_blocked',
            'database_connection_lost',
            'ai_analysis_timeout'
        ]
        
        for error_type in required_errors:
            assert error_type in self.handler.error_mappings
            mapping = self.handler.error_mappings[error_type]
            
            # Check required fields
            assert 'user_message' in mapping
            assert 'recovery_action' in mapping
            assert 'business_impact' in mapping
            assert 'internal_action' in mapping
            
            # Check messages are in Chinese as specified
            assert any(char >= '\u4e00' and char <= '\u9fff' for char in mapping['user_message'])
    
    def test_linkedin_rate_limit_handling(self):
        """Test LinkedIn rate limit error handling."""
        original_error = Exception("LinkedIn API rate limit exceeded")
        
        result = self.handler.handle_intelligent_error(
            'linkedin_rate_limit',
            original_error,
            self.context
        )
        
        assert result['user_message'] == 'LinkedIn搜索暫時受限，已自動切換到Indeed獲取更多職缺'
        assert result['recovery_attempted'] == True
        assert result['recovery_successful'] == True
        assert result['business_impact'] == 'maintain_user_experience'
        assert result['next_action'] == 'switch_to_indeed_scraper'
        assert result['estimated_recovery_time'] == '30秒'
        assert 'alternatives' in result
    
    def test_notion_api_error_handling(self):
        """Test Notion API error handling."""
        original_error = Exception("Notion API connection failed")
        
        result = self.handler.handle_intelligent_error(
            'notion_api_error',
            original_error,
            self.context
        )
        
        assert result['user_message'] == 'Notion同步暫時無法使用，數據已保存將稍後重試'
        assert result['recovery_attempted'] == True
        assert result['recovery_successful'] == True
        assert result['business_impact'] == 'user_retention_risk'
        assert result['next_action'] == 'add_to_retry_queue'
        assert 'estimated_recovery_time' in result
    
    def test_openai_quota_exceeded_handling(self):
        """Test OpenAI quota exceeded error handling."""
        original_error = Exception("OpenAI quota exceeded")
        
        result = self.handler.handle_intelligent_error(
            'openai_quota_exceeded',
            original_error,
            self.context
        )
        
        assert result['user_message'] == 'AI分析服務暫時繁忙，為您提供基礎匹配結果'
        assert result['recovery_attempted'] == True
        assert result['recovery_successful'] == True
        assert result['business_impact'] == 'reduced_value_delivery'
        assert result['next_action'] == 'use_basic_matching_algorithm'
        assert result['estimated_recovery_time'] == '即時'
    
    def test_unknown_error_type_fallback(self):
        """Test handling of unknown error types."""
        original_error = Exception("Unknown error")
        
        result = self.handler.handle_intelligent_error(
            'unknown_error_type',
            original_error,
            self.context
        )
        
        assert result['recovery_attempted'] == False
        assert result['business_impact'] == 'unknown'
        assert result['next_action'] == 'standard_error_flow'
        assert 'user_message' in result
    
    def test_recovery_metrics_tracking(self):
        """Test that recovery metrics are properly tracked."""
        original_error = Exception("Test error")
        
        # Execute multiple recovery actions
        self.handler.handle_intelligent_error('linkedin_rate_limit', original_error)
        self.handler.handle_intelligent_error('notion_api_error', original_error)
        self.handler.handle_intelligent_error('openai_quota_exceeded', original_error)
        
        metrics = self.handler.get_recovery_metrics()
        
        assert 'recovery_metrics' in metrics
        assert 'error_statistics' in metrics
        assert 'user_experience_score' in metrics
        
        # Check that counters were incremented
        recovery_metrics = metrics['recovery_metrics']
        assert recovery_metrics['user_satisfaction_maintained'] > 0
    
    def test_business_impact_tracking(self):
        """Test business impact tracking."""
        original_error = Exception("Test error")
        
        # Track different business impacts
        self.handler._track_business_impact('maintain_user_experience', 'test_error')
        self.handler._track_business_impact('user_retention_risk', 'test_error')
        self.handler._track_business_impact('service_disruption', 'test_error')
        
        metrics = self.handler.get_recovery_metrics()
        recovery_metrics = metrics['recovery_metrics']
        
        assert recovery_metrics.get('user_retention_risk_count', 0) > 0
        assert recovery_metrics.get('service_disruption_count', 0) > 0
    
    @patch('app.utils.error_handler.logger')
    def test_internal_actions_execution(self, mock_logger):
        """Test that internal actions are properly executed."""
        original_error = Exception("Test error")
        
        self.handler._execute_internal_action(
            'alert_support_team',
            'test_error',
            original_error,
            self.context
        )
        
        # Verify logger was called
        mock_logger.warning.assert_called()
    
    def test_ux_score_calculation(self):
        """Test user experience score calculation."""
        # Start with clean metrics
        handler = UserFriendlyErrorHandler()
        
        # Initially should be 100 (no errors)
        score = handler._calculate_ux_score()
        assert score == 100.0
        
        # Add some errors and recoveries
        handler.error_counts['test_error'] = 10
        handler.recovery_metrics['user_satisfaction_maintained'] = 8
        
        score = handler._calculate_ux_score()
        assert 0 <= score <= 100
        assert score == 80.0  # 8/10 * 100
    
    def test_recovery_action_failure_handling(self):
        """Test handling of recovery action failures."""
        original_error = Exception("Test error")
        
        # Mock a recovery action to fail
        with patch.object(self.handler, '_fallback_to_indeed', side_effect=Exception("Recovery failed")):
            result = self.handler._execute_recovery_action(
                'auto_fallback_indeed',
                original_error,
                {}
            )
            
            assert result['success'] == False
            assert 'error' in result
            assert result['next_action'] == 'manual_intervention_required'
    
    def test_additional_data_handling(self):
        """Test handling of additional data in error processing."""
        original_error = Exception("Test error")
        additional_data = {
            'retry_delay': 600,  # 10 minutes
            'retry_count': 2
        }
        
        result = self.handler.handle_intelligent_error(
            'notion_api_error',
            original_error,
            self.context,
            additional_data
        )
        
        assert result['recovery_attempted'] == True
        # Verify additional data was used in recovery
        assert '10分鐘' in result['estimated_recovery_time']
    
    def test_convenience_function(self):
        """Test the convenience function for intelligent error handling."""
        original_error = Exception("Test error")
        
        result = handle_intelligent_error(
            'linkedin_rate_limit',
            original_error,
            self.context
        )
        
        assert isinstance(result, dict)
        assert 'user_message' in result
        assert 'recovery_attempted' in result
        assert result['recovery_attempted'] == True


class TestErrorHandlerIntegration:
    """Integration tests for error handler with other components."""
    
    def test_error_context_creation(self):
        """Test error context creation and usage."""
        context = ErrorContext(
            user_id="user_123",
            request_id="req_456",
            endpoint="/api/v1/analysis",
            method="POST",
            additional_data={'job_id': 'job_789'}
        )
        
        assert context.user_id == "user_123"
        assert context.request_id == "req_456" 
        assert context.endpoint == "/api/v1/analysis"
        assert context.method == "POST"
        assert context.additional_data['job_id'] == 'job_789'
        assert isinstance(context.timestamp, datetime)
    
    @patch('app.utils.error_handler.logger')
    def test_logging_integration(self, mock_logger):
        """Test that errors are properly logged."""
        handler = UserFriendlyErrorHandler()
        original_error = Exception("Test error for logging")
        
        handler.handle_intelligent_error(
            'linkedin_rate_limit',
            original_error,
            ErrorContext(user_id="test_user")
        )
        
        # Verify logging was triggered
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args
        assert 'Intelligent error handling for linkedin_rate_limit' in call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__])