"""
Optimized Vector Service using ChromaDB with caching for better performance
"""
import os
import hashlib
from typing import Dict, Any, List
from functools import lru_cache

# Disable ChromaDB telemetry before importing chromadb
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

import chromadb
from chromadb.config import Settings
from utils.logging_config import get_logger

logger = get_logger('services.vector')

class VectorServiceOptimized:
    """
    Optimized service for ChromaDB vector database operations with caching
    """
    
    def __init__(self):
        self.chroma_path = os.getenv('CHROMA_DB_PATH', './chroma_db')
        # Disable telemetry to prevent PostHog errors
        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize collections
        self.resolutions_collection = self.client.get_or_create_collection(
            name="dispute_resolutions",
            metadata={"description": "Historical dispute resolutions"}
        )
        
        self.policies_collection = self.client.get_or_create_collection(
            name="company_policies",
            metadata={"description": "Company policies for dispute resolution"}
        )
    
    def get_similar_cases(self, case: 'DisputeCase', limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get similar historical cases from ChromaDB with caching
        """
        logger.info(f"Retrieving similar cases for {case.case_id}")
        
        # Create query text from case data
        query_text = self._create_case_query_text(case)
        
        # Use cached query for performance
        return self._query_similar_cases_cached(query_text, limit)
    
    @lru_cache(maxsize=128)
    def _query_similar_cases_cached(self, query_text: str, limit: int) -> List[Dict[str, Any]]:
        """
        Cached query for similar cases to improve performance
        """
        try:
            # Query the resolutions collection
            results = self.resolutions_collection.query(
                query_texts=[query_text],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            similar_cases = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 1.0
                    
                    similar_cases.append({
                        'case_id': metadata.get('case_id', 'Unknown'),
                        'dispute_type': metadata.get('dispute_type', 'Unknown'),
                        'amount': metadata.get('amount', 0),
                        'resolution': metadata.get('resolution', 'Unknown'),
                        'reason': doc,
                        'confidence': 1.0 - distance,
                        'similarity_score': 1.0 - distance
                    })
            
            logger.info(f"Found {len(similar_cases)} similar cases (cached)")
            return similar_cases
            
        except Exception as e:
            logger.error(f"Error querying similar cases: {e}")
            return []

    def get_relevant_policies(self, case: 'DisputeCase', limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get relevant company policies from ChromaDB with caching
        """
        logger.info(f"Retrieving policies for {case.case_id}")
        
        # Create query text from case data
        query_text = self._create_policy_query_text(case)
        
        # Use cached query for performance
        return self._query_policies_cached(query_text, limit)
    
    @lru_cache(maxsize=64)
    def _query_policies_cached(self, query_text: str, limit: int) -> List[Dict[str, Any]]:
        """
        Cached query for policies to improve performance
        """
        try:
            # Query the policies collection
            results = self.policies_collection.query(
                query_texts=[query_text],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            policies = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 1.0
                    
                    policies.append({
                        'policy_id': metadata.get('policy_id', 'Unknown'),
                        'title': metadata.get('title', 'Unknown'),
                        'content': doc,
                        'category': metadata.get('category', 'General'),
                        'relevance_score': 1.0 - distance
                    })
            
            logger.info(f"Found {len(policies)} relevant policies (cached)")
            return policies
            
        except Exception as e:
            logger.error(f"Error querying policies: {e}")
            return []

    def store_resolution(self, case: 'DisputeCase', resolution: 'Resolution') -> bool:
        """
        Store a new resolution in ChromaDB and clear cache (handles duplicates gracefully)
        """
        try:
            # Create document text
            doc_text = f"Resolution for case {case.case_id}: {resolution.reason}"
            
            # Create metadata with actual Salesforce IDs and current timestamp
            from datetime import datetime
            metadata = {
                'case_id': case.case_id,  # Actual Salesforce case ID
                'account_id': case.case_data.get('AccountId', 'Unknown'),  # Actual Salesforce account ID
                'dispute_type': case.case_data.get('Dispute_Type__c', 'Unknown'),
                'amount': case.case_data.get('Amount__c', 0),
                'resolution': resolution.action,
                'customer_segment': case.account_data.get('Customer_Segment__c', 'Standard'),
                'customer_name': case.account_data.get('Name', 'Unknown'),
                'timestamp': datetime.utcnow().isoformat()  # Current timestamp instead of hardcoded
            }
            
            # Create unique ID using actual case ID and timestamp
            unique_id = f"resolution_{case.case_id}_{metadata['timestamp'].replace(':', '').replace('-', '').replace('.', '')}"
            
            # Check if this resolution already exists for this case
            try:
                existing = self.resolutions_collection.get(
                    where={"case_id": case.case_id}
                )
                if existing['ids']:
                    logger.info(f"Resolution already exists for case {case.case_id}. Skipping storage.")
                    return True
            except Exception:
                pass  # Continue with storage if check fails
            
            # Add to collection
            self.resolutions_collection.add(
                documents=[doc_text],
                metadatas=[metadata],
                ids=[unique_id]
            )
            
            # Clear cache since we added new data
            self._query_similar_cases_cached.cache_clear()
            
            logger.info(f"Stored resolution for case {case.case_id} (SF Case ID) and cleared cache")
            logger.info(f"Account ID: {metadata['account_id']}, Customer: {metadata['customer_name']}")
            logger.info(f"ChromaDB ID: {unique_id}")
            return True
            
        except Exception as e:
            # Handle ChromaDB duplicate ID warnings gracefully
            if "existing embedding ID" in str(e).lower():
                logger.warning(f"Resolution already exists for case {case.case_id}. Skipping duplicate.")
                return True
            logger.error(f"Error storing resolution: {e}")
            return False

    def _create_case_query_text(self, case: 'DisputeCase') -> str:
        """
        Create query text for finding similar cases
        """
        dispute_type = case.case_data.get('Dispute_Type__c', '')
        amount = case.case_data.get('Amount__c', 0)
        description = case.case_data.get('Description', '')
        customer_segment = case.account_data.get('Customer_Segment__c', '')
        
        return f"Dispute type: {dispute_type}, Amount: {amount}, Description: {description}, Customer segment: {customer_segment}"
    
    def _create_policy_query_text(self, case: 'DisputeCase') -> str:
        """
        Create query text for finding relevant policies
        """
        dispute_type = case.case_data.get('Dispute_Type__c', '')
        amount = case.case_data.get('Amount__c', 0)
        customer_segment = case.account_data.get('Customer_Segment__c', '')
        
        return f"Policy for {dispute_type} disputes, amount {amount}, customer segment {customer_segment}" 