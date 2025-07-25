"""
LLM Service for generating resolutions using OpenAI API
"""
import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import openai
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
from utils.logging_config import get_logger

logger = get_logger('services.llm')

class ResolutionResponse(BaseModel):
    """Structured response model for LLM resolution recommendations"""
    action: Literal['full_refund', 'partial_refund', 'deny_refund', 'account_credit']
    amount: float = Field(ge=0, description="Amount to refund or credit")
    reason: str = Field(min_length=10, description="Detailed reason for decision")
    confidence: float = Field(ge=0, le=1, description="Confidence score 0-1")
    requires_human_review: bool = True
    supporting_factors: List[str] = Field(default=[], description="Key factors supporting the decision")
    risk_level: Literal['low', 'medium', 'high'] = Field(default='medium', description="Risk level of the decision")

class LLMService:
    """
    Service for LLM operations with comprehensive error handling, caching, and monitoring
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Initialize cache and metrics
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour cache TTL
        self.metrics = {
            'calls_made': 0,
            'cache_hits': 0,
            'failures': 0,
            'total_tokens': 0,
            'avg_response_time': 0.0,
            'successful_parses': 0,
            'fallback_used': 0
        }
        
        # Validate configuration
        if not os.getenv('OPENAI_API_KEY'):
            logger.warning("⚠️ [LLM] OpenAI API key not found, service will use fallback logic")
            self.client = None
    
    def generate_resolution(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate resolution using OpenAI API with fallback to rule-based logic
        """
        logger.info("🤖 [LLM] Generating resolution using OpenAI API")
        
        # Check cache first
        cache_key = self._get_cache_key(context)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info("📦 [LLM] Using cached response")
            self.metrics['cache_hits'] += 1
            return cached_result
        
        start_time = time.time()
        
        try:
            self.metrics['calls_made'] += 1
            
            # If no OpenAI client, use fallback
            if not self.client:
                logger.warning("⚠️ [LLM] No OpenAI client available, using fallback logic")
                return self._fallback_resolution(context)
            
            # Build the prompt
            prompt = self._build_resolution_prompt(context)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert dispute resolution analyst with deep knowledge of billing disputes, customer service, and financial risk management. Always prioritize customer satisfaction while protecting company interests."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1000
            )
            
            # Track metrics
            response_time = time.time() - start_time
            self._update_response_time(response_time)
            
            # Calculate cost and update metrics
            cost_info = self._calculate_cost(response.usage) if response.usage else {'total_cost': 0.0}
            if response.usage:
                self.metrics['total_tokens'] += response.usage.total_tokens
            
            # Parse and validate response
            resolution_data = self._parse_llm_response(response.choices[0].message.content)
            
            # Add cost information to the response
            resolution_data['cost_info'] = cost_info
            
            # Cache the result
            self._cache_result(cache_key, resolution_data)
            
            logger.info(f"✅ [LLM] Successfully generated resolution: {resolution_data['action']} - ${resolution_data['amount']} (Cost: ${cost_info['total_cost']:.4f})")
            return resolution_data
            
        except Exception as e:
            logger.error(f"❌ [LLM] Error calling OpenAI API: {e}")
            self.metrics['failures'] += 1
            return self._fallback_resolution(context)
    
    def _build_resolution_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build comprehensive prompt for LLM with all available context
        """
        case = context.get('case', {})
        account = context.get('account', {})
        subscription = context.get('subscription', {})
        charges = context.get('charges', {})
        similar_cases = context.get('similar_cases', [])
        policies = context.get('policies', [])
        
        prompt = f"""
You are analyzing a billing dispute case. Please provide a comprehensive resolution recommendation.

CASE INFORMATION:
- Case ID: {case.get('Id', 'Unknown')}
- Customer: {account.get('Name', 'Unknown')} ({account.get('Customer_Segment__c', 'Standard')} tier)
- Dispute Type: {case.get('Dispute_Type__c', 'Unknown')}
- Disputed Amount: ${case.get('Amount__c', 0)}
- Case Description: {case.get('Description', 'No description provided')}
- Case Status: {case.get('Status', 'Unknown')}
- Case Priority: {case.get('Priority', 'Medium')}
- Created Date: {case.get('CreatedDate', 'Unknown')}

CUSTOMER PROFILE:
- Customer Segment: {account.get('Customer_Segment__c', 'Standard')}
- Account Type: {account.get('Type', 'Unknown')}
- Phone: {account.get('Phone', 'Not provided')}
- Email: {account.get('Email__c', 'Not provided')}
- Country: {account.get('BillingCountry', 'Unknown')}
- State: {account.get('BillingState', 'Unknown')}

SUBSCRIPTION DATA:
{self._format_subscription_data(subscription)}

PAYMENT HISTORY:
{self._format_payment_history(charges)}

HISTORICAL CONTEXT (Similar Cases):
{self._format_similar_cases(similar_cases)}

COMPANY POLICIES:
{self._format_policies(policies)}

ANALYSIS GUIDELINES:
1. Consider customer tier and loyalty
2. Evaluate dispute legitimacy based on evidence
3. Balance customer satisfaction with company interests
4. Consider precedent from similar cases
5. Follow company policies and guidelines
6. Assess financial impact and risk level

Please respond with a JSON object containing:
{{
    "action": "full_refund|partial_refund|deny_refund|account_credit",
    "amount": <numeric_amount_to_refund_or_credit>,
    "reason": "<detailed_explanation_of_decision>",
    "confidence": <confidence_score_0_to_1>,
    "requires_human_review": true,
    "supporting_factors": ["<factor1>", "<factor2>", "<factor3>"],
    "risk_level": "low|medium|high"
}}

Key considerations:
- Premium customers deserve higher consideration
- Small amounts (<$50) favor customer satisfaction
- Large amounts (>$500) require careful analysis
- Service outages typically warrant full refunds
- Billing errors should be corrected promptly
- Always require human review for final approval
"""
        
        return prompt
    
    def _format_subscription_data(self, subscription: Dict[str, Any]) -> str:
        """Format subscription data for prompt"""
        if not subscription:
            return "No subscription data available."
        
        return f"""
- Subscription ID: {subscription.get('id', 'Unknown')}
- Status: {subscription.get('status', 'Unknown')}
- Plan: {subscription.get('plan_name', 'Unknown')}
- Monthly Amount: ${subscription.get('monthly_amount', 0)}
- Start Date: {subscription.get('start_date', 'Unknown')}
- Next Billing: {subscription.get('next_billing_date', 'Unknown')}
"""
    
    def _format_payment_history(self, charges: Dict[str, Any]) -> str:
        """Format payment history for prompt"""
        if not charges or not charges.get('data'):
            return "No payment history available."
        
        formatted = []
        for charge in charges.get('data', [])[:5]:  # Last 5 charges
            formatted.append(f"- {charge.get('created', 'Unknown')}: ${charge.get('amount', 0)/100:.2f} ({charge.get('status', 'Unknown')})")
        
        return "\n".join(formatted) if formatted else "No recent charges found."
    
    def _format_similar_cases(self, cases: List[Dict[str, Any]]) -> str:
        """Format similar cases for prompt"""
        if not cases:
            return "No similar cases found."
        
        formatted = []
        for case in cases[:3]:  # Top 3 similar cases
            formatted.append(f"- Case {case.get('case_id', 'Unknown')}: ${case.get('amount', 0)} - {case.get('resolution', 'Unknown')} ({case.get('reason', 'No reason provided')})")
        
        return "\n".join(formatted)
    
    def _format_policies(self, policies: List[Dict[str, Any]]) -> str:
        """Format policies for prompt"""
        if not policies:
            return "No relevant policies found."
        
        formatted = []
        for policy in policies[:3]:  # Top 3 relevant policies
            formatted.append(f"- {policy.get('title', 'Unknown Policy')}: {policy.get('content', 'No content available')}")
        
        return "\n".join(formatted)
    
    def _parse_llm_response(self, response_content: str) -> Dict[str, Any]:
        """Parse and validate LLM response"""
        try:
            # Parse JSON response
            response_data = json.loads(response_content)
            
            # Validate using Pydantic model
            resolution = ResolutionResponse(**response_data)
            
            # Convert to dict and ensure safety requirements
            result = resolution.dict()
            result['requires_human_review'] = True  # Always require human review
            
            self.metrics['successful_parses'] += 1
            return result
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"❌ [LLM] Error parsing LLM response: {e}")
            logger.error(f"❌ [LLM] Raw response: {response_content}")
            raise ValueError(f"Invalid LLM response format: {e}")
    
    def _fallback_resolution(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback resolution logic when LLM fails"""
        logger.info("🔄 [LLM] Using fallback resolution logic")
        self.metrics['fallback_used'] += 1
        
        try:
            case = context.get('case', {})
            amount = float(case.get('Amount__c', 0))
            dispute_type = case.get('Dispute_Type__c', '').lower()
            customer_segment = context.get('account', {}).get('Customer_Segment__c', 'Standard')
            
            # Rule-based fallback logic
            if amount < 50:
                return {
                    'action': 'full_refund',
                    'amount': amount,
                    'reason': 'Small amount dispute - approved for customer satisfaction (fallback logic)',
                    'confidence': 0.8,
                    'requires_human_review': True,
                    'supporting_factors': ['Small amount', 'Customer satisfaction priority'],
                    'risk_level': 'low',
                    'cost_info': {'total_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}
                }
            elif amount < 200:
                refund_amount = amount * 0.75 if customer_segment == 'Premium' else amount * 0.5
                return {
                    'action': 'partial_refund',
                    'amount': refund_amount,
                    'reason': f'Medium amount dispute - partial refund based on {customer_segment} tier (fallback logic)',
                    'confidence': 0.6,
                    'requires_human_review': True,
                    'supporting_factors': ['Medium amount', f'{customer_segment} customer tier'],
                    'risk_level': 'medium',
                    'cost_info': {'total_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}
                }
            else:
                return {
                    'action': 'deny_refund',
                    'amount': 0,
                    'reason': 'High amount dispute - requires detailed manual review (fallback logic)',
                    'confidence': 0.4,
                    'requires_human_review': True,
                    'supporting_factors': ['High financial impact', 'Requires detailed investigation'],
                    'risk_level': 'high',
                    'cost_info': {'total_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}
                }
                
        except Exception as e:
            logger.error(f"❌ [LLM] Error in fallback logic: {e}")
            return {
                'action': 'deny_refund',
                'amount': 0,
                'reason': 'Error in resolution generation - manual review required',
                'confidence': 0.0,
                'requires_human_review': True,
                'supporting_factors': ['System error'],
                'risk_level': 'high',
                'cost_info': {'total_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}
            }
    
    def _calculate_cost(self, usage) -> Dict[str, Any]:
        """Calculate cost based on OpenAI token usage"""
        if not usage:
            return {'total_cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'input_cost': 0.0, 'output_cost': 0.0}
        
        # OpenAI pricing for GPT-4o-mini (as of 2024)
        # Input: $0.150 per 1M tokens, Output: $0.600 per 1M tokens
        input_cost_per_1m = 0.150
        output_cost_per_1m = 0.600
        
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        
        # Calculate costs
        input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * output_cost_per_1m
        total_cost = input_cost + output_cost
        
        return {
            'total_cost': round(total_cost, 6),
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6)
        }
    
    def _get_cache_key(self, context: Dict[str, Any]) -> str:
        """Generate cache key for context"""
        # Create a simplified context for caching (remove timestamps, etc.)
        cache_context = {
            'case_id': context.get('case', {}).get('Id', ''),
            'amount': context.get('case', {}).get('Amount__c', 0),
            'dispute_type': context.get('case', {}).get('Dispute_Type__c', ''),
            'customer_segment': context.get('account', {}).get('Customer_Segment__c', ''),
            'similar_cases_count': len(context.get('similar_cases', [])),
            'policies_count': len(context.get('policies', []))
        }
        
        context_str = json.dumps(cache_context, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache if still valid"""
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=self.cache_ttl):
                return cached_data['result']
            else:
                # Remove expired cache entry
                del self.cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache the result with timestamp"""
        self.cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        # Simple cache cleanup - remove old entries if cache gets too large
        if len(self.cache) > 100:
            # Remove oldest entries
            sorted_cache = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])
            for key, _ in sorted_cache[:10]:  # Remove oldest 10 entries
                del self.cache[key]
    
    def _update_response_time(self, response_time: float) -> None:
        """Update average response time metric"""
        if self.metrics['calls_made'] > 0:
            self.metrics['avg_response_time'] = (
                (self.metrics['avg_response_time'] * (self.metrics['calls_made'] - 1) + response_time) 
                / self.metrics['calls_made']
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics for monitoring"""
        return {
            **self.metrics,
            'cache_hit_rate': self.metrics['cache_hits'] / max(self.metrics['calls_made'], 1),
            'success_rate': (self.metrics['calls_made'] - self.metrics['failures']) / max(self.metrics['calls_made'], 1),
            'cache_size': len(self.cache),
            'service_status': 'healthy' if self.client else 'degraded'
        }
    
    def clear_cache(self) -> None:
        """Clear the cache (useful for testing)"""
        self.cache.clear()
        logger.info("🧹 [LLM] Cache cleared")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        status = {
            'service': 'LLMService',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'openai_configured': self.client is not None,
            'model': self.model,
            'cache_size': len(self.cache),
            'total_calls': self.metrics['calls_made']
        }
        
        if not self.client:
            status['status'] = 'degraded'
            status['warning'] = 'OpenAI API key not configured'
        
        return status 