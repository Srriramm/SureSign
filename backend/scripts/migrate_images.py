#!/usr/bin/env python
"""
Azure Blob Storage Migration Script

This script helps migrate images from legacy Azure Blob Storage containers
to the new secure container structure. It handles:

1. User selfies migration
2. Property images migration
3. Property documents migration
4. User database record updates
5. Updating URLs with secure container references

Usage:
    python migrate_images.py [options]

Options:
    --dry-run       Show what would be migrated without actually migrating
    --container=X   Migrate only specified container
    --help          Show this help message
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
import httpx
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("migration")

# Load environment variables
load_dotenv()

# Auth setup
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'adminpassword')

class ImageMigrator:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.token = None
        self.headers = {}
        self.api_url = API_BASE_URL
        self.migration_tasks = {}
        
    async def authenticate(self):
        """Authenticate with the API to get token"""
        logger.info("Authenticating with API...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/auth/login/admin",
                    data={
                        "email": ADMIN_EMAIL,
                        "password": ADMIN_PASSWORD
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data["access_token"]
                    self.headers = {
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    }
                    logger.info("Authentication successful")
                    return True
                else:
                    logger.error(f"Authentication failed: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
            
    async def start_migration(self):
        """Start migration tasks for all containers"""
        if not await self.authenticate():
            logger.error("Migration aborted: Authentication failed")
            return
            
        if self.dry_run:
            logger.info("DRY RUN: No actual migration will be performed")
            
        logger.info("Starting migration process...")
        
        try:
            # Start the selfie migration task
            migration_id = await self.start_selfie_migration()
            
            if not migration_id:
                logger.error("Failed to start selfie migration")
                return
                
            # Monitor migration progress
            task_status = await self.monitor_migration(migration_id)
            
            # Summarize results
            if task_status:
                self.summarize_migration(task_status)
            else:
                logger.error("Failed to retrieve migration status")
                
        except Exception as e:
            logger.error(f"Migration error: {str(e)}")
        
    async def start_selfie_migration(self):
        """Start the selfie migration process"""
        if self.dry_run:
            logger.info("DRY RUN: Would start selfie migration")
            return "dry-run-task-id"
            
        logger.info("Starting selfie migration...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/auth/migrate-selfies",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    task_id = data.get("task_id")
                    logger.info(f"Migration started with task ID: {task_id}")
                    return task_id
                else:
                    logger.error(f"Failed to start migration: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error starting migration: {str(e)}")
            return None
            
    async def get_migration_status(self, task_id):
        """Get the status of a migration task"""
        if self.dry_run:
            logger.info(f"DRY RUN: Would check status of task {task_id}")
            return {"status": "completed", "progress": 100}
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/auth/migration-status/{task_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get migration status: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error getting migration status: {str(e)}")
            return None
            
    async def monitor_migration(self, task_id, check_interval=5):
        """Monitor migration progress until completion"""
        if self.dry_run:
            logger.info("DRY RUN: Would monitor migration progress")
            await asyncio.sleep(1)
            return {"status": "completed", "progress": 100}
            
        logger.info(f"Monitoring migration task {task_id}...")
        
        completed_statuses = ["completed", "failed"]
        last_progress = -1
        
        while True:
            status_data = await self.get_migration_status(task_id)
            
            if not status_data:
                logger.error("Failed to retrieve migration status")
                return None
                
            current_status = status_data.get("status")
            current_progress = status_data.get("progress", 0)
            
            # Log progress updates
            if current_progress != last_progress:
                logger.info(f"Migration progress: {current_progress}%")
                last_progress = current_progress
                
            # Check if migration has completed
            if current_status in completed_statuses:
                logger.info(f"Migration {current_status} with {current_progress}% progress")
                return status_data
                
            # Wait before checking again
            await asyncio.sleep(check_interval)
            
    def summarize_migration(self, status_data):
        """Summarize the migration results"""
        logger.info("=== Migration Summary ===")
        
        if not status_data:
            logger.info("No migration data available")
            return
            
        # Print basic summary
        logger.info(f"Status: {status_data.get('status', 'Unknown')}")
        logger.info(f"Progress: {status_data.get('progress', 0)}%")
        
        # Print time information
        start_time = status_data.get('start_time')
        end_time = status_data.get('end_time')
        if start_time and end_time:
            logger.info(f"Start time: {start_time}")
            logger.info(f"End time: {end_time}")
            
        # Print migration statistics
        summary = status_data.get('summary', {})
        if summary:
            logger.info(f"Total blobs found: {summary.get('total_found', 0)}")
            logger.info(f"Total migrated: {summary.get('total_migrated', 0)}")
            logger.info(f"Total failed: {summary.get('total_failed', 0)}")
            
        # Print container errors
        container_errors = status_data.get('container_errors', [])
        if container_errors:
            logger.info("Container errors:")
            for error in container_errors:
                logger.info(f"  - {error.get('container')}: {error.get('error')}")
                
        # Print results summary
        results = status_data.get('results', [])
        if results:
            success_count = sum(1 for r in results if r.get('status') == 'success')
            failed_count = sum(1 for r in results if r.get('status') == 'failed')
            
            logger.info(f"Results: {len(results)} items processed")
            logger.info(f"  - Success: {success_count}")
            logger.info(f"  - Failed: {failed_count}")
            
            # Log failed items
            if failed_count > 0:
                logger.info("Failed migrations:")
                for item in results:
                    if item.get('status') == 'failed':
                        logger.info(f"  - {item.get('blob_name')}: {item.get('error')}")
                        
        logger.info("=== End of Summary ===")

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Azure Blob Storage Migration Script")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without actually migrating")
    parser.add_argument("--container", help="Migrate only specified container")
    args = parser.parse_args()
    
    # Execute migration
    migrator = ImageMigrator(dry_run=args.dry_run)
    await migrator.start_migration()
    
if __name__ == "__main__":
    asyncio.run(main()) 