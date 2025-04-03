import asyncio
import os
import json
from web3 import Web3
import logging
import traceback

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class BlockchainService:
    @classmethod
    async def create(cls):
        """Factory method to create a BlockchainService instance"""
        instance = cls()
        return instance

    def __init__(self):
        infura_url = os.getenv('INFURA_URL')
        if not infura_url:
            raise ValueError("INFURA_URL environment variable not set")

        try:
            self.w3 = Web3(Web3.HTTPProvider(infura_url))
            if not self.w3.is_connected():
                raise ConnectionError("Failed to connect to Ethereum network")

            logger.info(f"Connected to Ethereum network: {infura_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Ethereum network: {e}")
            raise

        self.contract_address = os.getenv('CONTRACT_ADDRESS')
        if not self.contract_address or not Web3.is_address(self.contract_address):
            raise ValueError("Invalid contract address in environment variables")

        self.contract_address = Web3.to_checksum_address(self.contract_address)
        
        # Simplified account setup
        private_key = os.getenv('ETHEREUM_PRIVATE_KEY')
        if not private_key:
            raise ValueError("Ethereum private key not found in environment variables")

        account = self.w3.eth.account.from_key(private_key)
        self.w3.eth.default_account = account.address
        self._account = account

    async def store_document_hash(self, document_hash: str) -> str:
        """
        Asynchronously store a document hash on the blockchain
        
        :param document_hash: SHA-256 hash of the document
        :return: Transaction hash if successful
        """
        loop = asyncio.get_event_loop()
        
        try:
            logger.info(f"Attempting to store document hash: {document_hash}")

            # Validate input hash
            if not document_hash or len(document_hash) != 64:
                logger.error(f"Invalid document hash format: {document_hash}")
                raise ValueError("Document hash must be a 64-character hexadecimal string")

            # Prepare transaction
            def prepare_transaction():
                nonce = self.w3.eth.get_transaction_count(self._account.address)
                gas_price = self.w3.eth.gas_price
                
                transaction = {
                    'nonce': nonce,
                    'to': self.contract_address,
                    'value': 0,
                    'gas': 100000,  # Adjust as needed
                    'gasPrice': gas_price,
                    'data': document_hash.encode('utf-8')
                }
                
                return transaction
            
            transaction = await loop.run_in_executor(None, prepare_transaction)
            
            # Sign transaction
            def sign_transaction():
                signed_txn = self._account.sign_transaction(transaction)
                return signed_txn
            
            signed_txn = await loop.run_in_executor(None, sign_transaction)
            
            # Send transaction
            def send_transaction():
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                return tx_hash
            
            tx_hash = await loop.run_in_executor(None, send_transaction)
            
            logger.info(f"Document hash stored successfully: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Error storing document hash: {e}")
            logger.error(traceback.format_exc())
            raise