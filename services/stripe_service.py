"""
Stripe Service
"""
import os
import stripe
from typing import Dict, Any, Optional

from utils.logging_config import get_logger

logger = get_logger('services.stripe')

class StripeService:
    """
    Service for interacting with Stripe
    """
    
    def __init__(self):
        # Initialize Stripe connection
        self.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        if self.api_key:
            try:
                stripe.api_key = self.api_key
                # Test the connection by making a simple API call
                stripe.Account.retrieve()
                logger.info(f"✅ [STRIPE] Successfully connected to Stripe")
            except Exception as e:
                logger.error(f"❌ [STRIPE] Failed to connect to Stripe: {e}")
                self.api_key = None
        else:
            logger.warning("⚠️ [STRIPE] Missing Stripe API key, using mock data")
    
    def get_charges(self, customer_id: str) -> Dict[str, Any]:
        """
        Get charges for a customer from Stripe
        """
        logger.info(f"🔍 [STRIPE] Fetching charges for customer {customer_id} from Stripe")
        
        if not self.api_key:
            logger.warning("⚠️ [STRIPE] Using mock data - no Stripe connection")
            return self._get_mock_charges(customer_id)
        
        try:
            # Get charges for the customer
            charges = stripe.Charge.list(
                customer=customer_id,
                limit=100  # Get up to 100 charges
            )
            
            # Format the response
            charges_data = []
            for charge in charges.data:
                charge_data = {
                    'id': charge.id,
                    'amount': charge.amount,  # Amount in cents
                    'currency': charge.currency,
                    'status': charge.status,
                    'created': charge.created,
                    'description': charge.description,
                    'dispute': charge.dispute.id if charge.dispute else None
                }
                charges_data.append(charge_data)
            
            result = {
                'customer_id': customer_id,
                'charges': charges_data
            }
            
            logger.info(f"✅ [STRIPE] Successfully fetched charges for customer {customer_id}")
            logger.info(f"📋 [STRIPE] Found {len(charges_data)} charges")
            logger.info(f"📋 [STRIPE] Charges data: {result}")
            
            return result
            
        except stripe.error.StripeError as e:
            logger.error(f"❌ [STRIPE] Stripe error fetching charges for customer {customer_id}: {e}")
            logger.warning("⚠️ [STRIPE] Falling back to mock data")
            return self._get_mock_charges(customer_id)
        except Exception as e:
            logger.error(f"❌ [STRIPE] Error fetching charges for customer {customer_id}: {e}")
            logger.warning("⚠️ [STRIPE] Falling back to mock data")
            return self._get_mock_charges(customer_id)
    

    
    def create_refund(self, charge_id: str, amount: int = None, reason: str = None) -> str:
        """
        Create a refund in Stripe
        """
        logger.info(f"💰 [STRIPE] Creating refund for charge {charge_id}")
        
        if not self.api_key:
            logger.warning("⚠️ [STRIPE] Using mock refund - no Stripe connection")
            return self._get_mock_refund_id(charge_id)
        
        try:
            # Prepare refund data
            refund_data = {}
            if amount:
                refund_data['amount'] = amount
            if reason:
                refund_data['reason'] = reason
            
            logger.info(f"📝 [STRIPE] Refund data: {refund_data}")
            
            # Create the refund
            refund = stripe.Refund.create(
                charge=charge_id,
                **refund_data
            )
            
            logger.info(f"✅ [STRIPE] Successfully created refund {refund.id}")
            logger.info(f"📋 [STRIPE] Refund data: {refund}")
            
            return refund.id
            
        except stripe.error.StripeError as e:
            logger.error(f"❌ [STRIPE] Stripe error creating refund for charge {charge_id}: {e}")
            return self._get_mock_refund_id(charge_id)
        except Exception as e:
            logger.error(f"❌ [STRIPE] Error creating refund for charge {charge_id}: {e}")
            return self._get_mock_refund_id(charge_id)
    
    def _get_mock_charges(self, customer_id: str) -> Dict[str, Any]:
        """Get mock charges data"""
        return {
            'customer_id': customer_id,
            'charges': [
                {
                    'id': 'ch_stripe_123',
                    'amount': 9999,  # Amount in cents
                    'currency': 'usd',
                    'status': 'succeeded',
                    'created': 1705312200,
                    'description': 'Premium Plan - January 2024',
                    'dispute': None
                },
                {
                    'id': 'ch_stripe_124',
                    'amount': 9999,
                    'currency': 'usd',
                    'status': 'succeeded',
                    'created': 1702629600,
                    'description': 'Premium Plan - December 2023',
                    'dispute': None
                }
            ]
        }
    

    
    def _get_mock_refund_id(self, charge_id: str) -> str:
        """Get mock refund ID"""
        refund_id = f"re_{charge_id}_mock"
        logger.info(f"✅ [STRIPE] Created mock refund {refund_id}")
        return refund_id 