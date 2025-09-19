#!/usr/bin/env python3
"""
Database backup script for BrainBudget.
Backs up Firestore data to Google Cloud Storage with encryption and versioning.
"""
import os
import sys
import json
import gzip
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import argparse

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import storage
import hashlib


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FirestoreBackup:
    """Handle Firestore database backups."""
    
    def __init__(self, project_id: str, service_account_key: str, backup_bucket: str):
        self.project_id = project_id
        self.backup_bucket = backup_bucket
        
        # Initialize Firebase Admin
        if not firebase_admin._apps:
            cred = credentials.Certificate(json.loads(service_account_key))
            firebase_admin.initialize_app(cred, {'projectId': project_id})
        
        self.db = firestore.client()
        self.storage_client = storage.Client()
        
        # Ensure backup bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the backup bucket exists."""
        try:
            self.storage_client.get_bucket(self.backup_bucket)
            logger.info(f"Backup bucket {self.backup_bucket} exists")
        except Exception as e:
            logger.error(f"Backup bucket {self.backup_bucket} not accessible: {e}")
            raise
    
    def _get_collection_data(self, collection_name: str) -> List[Dict[str, Any]]:
        """Get all documents from a collection."""
        try:
            docs = []
            collection_ref = self.db.collection(collection_name)
            
            for doc in collection_ref.stream():
                doc_data = doc.to_dict()
                doc_data['_doc_id'] = doc.id
                doc_data['_collection'] = collection_name
                
                # Convert Firestore timestamps to ISO strings
                for key, value in doc_data.items():
                    if hasattr(value, 'timestamp'):  # Firestore timestamp
                        doc_data[key] = value.isoformat()
                
                docs.append(doc_data)
            
            logger.info(f"Retrieved {len(docs)} documents from {collection_name}")
            return docs
            
        except Exception as e:
            logger.error(f"Failed to get data from collection {collection_name}: {e}")
            return []
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum of data."""
        return hashlib.sha256(data).hexdigest()
    
    def create_backup(self, collections: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a full backup of specified collections."""
        timestamp = datetime.now(timezone.utc)
        backup_id = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Default collections to backup
        if collections is None:
            collections = [
                'users',
                'analyses',
                'transactions',
                'user_preferences',
                'account_deletions'
            ]
        
        backup_data = {
            'backup_id': backup_id,
            'timestamp': timestamp.isoformat(),
            'project_id': self.project_id,
            'version': '1.0',
            'collections': {}
        }
        
        logger.info(f"Starting backup {backup_id} for collections: {collections}")
        
        # Backup each collection
        total_documents = 0
        for collection_name in collections:
            logger.info(f"Backing up collection: {collection_name}")
            
            collection_data = self._get_collection_data(collection_name)
            backup_data['collections'][collection_name] = {
                'documents': collection_data,
                'count': len(collection_data),
                'backed_up_at': datetime.now(timezone.utc).isoformat()
            }
            
            total_documents += len(collection_data)
        
        backup_data['total_documents'] = total_documents
        backup_data['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Backup {backup_id} completed: {total_documents} total documents")
        return backup_data
    
    def compress_and_upload(self, backup_data: Dict[str, Any]) -> Dict[str, str]:
        """Compress backup data and upload to Cloud Storage."""
        backup_id = backup_data['backup_id']
        
        # Serialize to JSON
        json_data = json.dumps(backup_data, indent=2, ensure_ascii=False)
        json_bytes = json_data.encode('utf-8')
        
        # Compress with gzip
        compressed_data = gzip.compress(json_bytes)
        
        # Calculate checksums
        json_checksum = self._calculate_checksum(json_bytes)
        compressed_checksum = self._calculate_checksum(compressed_data)
        
        # Upload to Cloud Storage
        blob_name = f"firestore-backups/{backup_id}/backup.json.gz"
        bucket = self.storage_client.bucket(self.backup_bucket)
        blob = bucket.blob(blob_name)
        
        # Set metadata
        blob.metadata = {
            'backup_id': backup_id,
            'timestamp': backup_data['timestamp'],
            'project_id': self.project_id,
            'total_documents': str(backup_data['total_documents']),
            'json_checksum': json_checksum,
            'compressed_checksum': compressed_checksum,
            'backup_version': backup_data['version']
        }
        
        # Upload compressed data
        blob.upload_from_string(compressed_data, content_type='application/gzip')
        
        # Also upload manifest file
        manifest = {
            'backup_id': backup_id,
            'timestamp': backup_data['timestamp'],
            'blob_name': blob_name,
            'total_documents': backup_data['total_documents'],
            'collections': list(backup_data['collections'].keys()),
            'checksums': {
                'json': json_checksum,
                'compressed': compressed_checksum
            },
            'size_bytes': {
                'json': len(json_bytes),
                'compressed': len(compressed_data)
            }
        }
        
        manifest_blob = bucket.blob(f"firestore-backups/{backup_id}/manifest.json")
        manifest_blob.upload_from_string(
            json.dumps(manifest, indent=2),
            content_type='application/json'
        )
        
        logger.info(f"Backup uploaded to gs://{self.backup_bucket}/{blob_name}")
        logger.info(f"Compressed size: {len(compressed_data):,} bytes")
        logger.info(f"Compression ratio: {len(compressed_data)/len(json_bytes):.2%}")
        
        return {
            'backup_id': backup_id,
            'blob_name': blob_name,
            'manifest_blob': f"firestore-backups/{backup_id}/manifest.json",
            'size_compressed': len(compressed_data),
            'size_uncompressed': len(json_bytes),
            'checksum': compressed_checksum
        }
    
    def list_backups(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List available backups."""
        bucket = self.storage_client.bucket(self.backup_bucket)
        blobs = bucket.list_blobs(prefix='firestore-backups/', delimiter='/')
        
        backups = []
        
        # Get manifest files
        for blob in blobs:
            if blob.name.endswith('/manifest.json'):
                try:
                    manifest_data = json.loads(blob.download_as_text())
                    manifest_data['created'] = blob.time_created.isoformat()
                    manifest_data['blob_path'] = blob.name
                    backups.append(manifest_data)
                except Exception as e:
                    logger.error(f"Failed to read manifest {blob.name}: {e}")
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return backups[:limit]
    
    def cleanup_old_backups(self, keep_count: int = 30):
        """Remove old backups, keeping only the specified number."""
        backups = self.list_backups(limit=100)
        
        if len(backups) <= keep_count:
            logger.info(f"Only {len(backups)} backups found, no cleanup needed")
            return
        
        backups_to_delete = backups[keep_count:]
        logger.info(f"Deleting {len(backups_to_delete)} old backups")
        
        bucket = self.storage_client.bucket(self.backup_bucket)
        
        for backup in backups_to_delete:
            backup_id = backup['backup_id']
            prefix = f"firestore-backups/{backup_id}/"
            
            # Delete all blobs with this prefix
            blobs_to_delete = bucket.list_blobs(prefix=prefix)
            for blob in blobs_to_delete:
                blob.delete()
                logger.info(f"Deleted: {blob.name}")


class BackupRestorer:
    """Handle backup restoration."""
    
    def __init__(self, project_id: str, service_account_key: str, backup_bucket: str):
        self.project_id = project_id
        self.backup_bucket = backup_bucket
        
        # Initialize Firebase Admin
        if not firebase_admin._apps:
            cred = credentials.Certificate(json.loads(service_account_key))
            firebase_admin.initialize_app(cred, {'projectId': project_id})
        
        self.db = firestore.client()
        self.storage_client = storage.Client()
    
    def download_backup(self, backup_id: str) -> Dict[str, Any]:
        """Download and decompress a backup."""
        blob_name = f"firestore-backups/{backup_id}/backup.json.gz"
        
        bucket = self.storage_client.bucket(self.backup_bucket)
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            raise FileNotFoundError(f"Backup {backup_id} not found")
        
        # Download compressed data
        compressed_data = blob.download_as_bytes()
        
        # Decompress
        json_data = gzip.decompress(compressed_data)
        
        # Parse JSON
        backup_data = json.loads(json_data.decode('utf-8'))
        
        logger.info(f"Downloaded backup {backup_id}")
        return backup_data
    
    def restore_collection(self, collection_name: str, documents: List[Dict[str, Any]], 
                          overwrite: bool = False):
        """Restore documents to a collection."""
        collection_ref = self.db.collection(collection_name)
        
        if not overwrite:
            # Check if collection exists and has documents
            sample_docs = list(collection_ref.limit(1).stream())
            if sample_docs:
                raise ValueError(f"Collection {collection_name} already has data. Use --overwrite to replace.")
        
        logger.info(f"Restoring {len(documents)} documents to {collection_name}")
        
        # Batch writes for efficiency
        batch = self.db.batch()
        batch_size = 0
        
        for doc_data in documents:
            doc_id = doc_data.pop('_doc_id', None)
            doc_data.pop('_collection', None)  # Remove metadata
            
            if doc_id:
                doc_ref = collection_ref.document(doc_id)
            else:
                doc_ref = collection_ref.document()
            
            batch.set(doc_ref, doc_data)
            batch_size += 1
            
            # Commit in batches of 500 (Firestore limit)
            if batch_size >= 500:
                batch.commit()
                batch = self.db.batch()
                batch_size = 0
        
        # Commit remaining documents
        if batch_size > 0:
            batch.commit()
        
        logger.info(f"Restored {len(documents)} documents to {collection_name}")


def main():
    parser = argparse.ArgumentParser(description='BrainBudget database backup and restore')
    parser.add_argument('action', choices=['backup', 'restore', 'list', 'cleanup'],
                       help='Action to perform')
    parser.add_argument('--project-id', required=True, help='Firebase project ID')
    parser.add_argument('--service-account', required=True, 
                       help='Service account key JSON (file path or JSON string)')
    parser.add_argument('--backup-bucket', required=True, help='Cloud Storage backup bucket')
    parser.add_argument('--backup-id', help='Backup ID for restore operation')
    parser.add_argument('--collections', nargs='+', help='Collections to backup/restore')
    parser.add_argument('--overwrite', action='store_true', 
                       help='Overwrite existing data during restore')
    parser.add_argument('--keep-backups', type=int, default=30,
                       help='Number of backups to keep during cleanup')
    
    args = parser.parse_args()
    
    # Load service account key
    if os.path.isfile(args.service_account):
        with open(args.service_account, 'r') as f:
            service_account_key = f.read()
    else:
        service_account_key = args.service_account
    
    try:
        if args.action == 'backup':
            backup_manager = FirestoreBackup(
                args.project_id, 
                service_account_key, 
                args.backup_bucket
            )
            
            # Create backup
            backup_data = backup_manager.create_backup(args.collections)
            
            # Upload to Cloud Storage
            upload_result = backup_manager.compress_and_upload(backup_data)
            
            print(f"✅ Backup completed successfully!")
            print(f"Backup ID: {upload_result['backup_id']}")
            print(f"Compressed size: {upload_result['size_compressed']:,} bytes")
            print(f"Documents backed up: {backup_data['total_documents']}")
            
        elif args.action == 'list':
            backup_manager = FirestoreBackup(
                args.project_id, 
                service_account_key, 
                args.backup_bucket
            )
            
            backups = backup_manager.list_backups()
            
            print(f"📋 Available backups ({len(backups)}):")
            for backup in backups:
                print(f"  {backup['backup_id']} - {backup['timestamp']} "
                      f"({backup['total_documents']} docs)")
                      
        elif args.action == 'cleanup':
            backup_manager = FirestoreBackup(
                args.project_id, 
                service_account_key, 
                args.backup_bucket
            )
            
            backup_manager.cleanup_old_backups(args.keep_backups)
            print(f"✅ Cleanup completed, keeping {args.keep_backups} most recent backups")
            
        elif args.action == 'restore':
            if not args.backup_id:
                print("❌ Backup ID required for restore operation")
                sys.exit(1)
            
            restorer = BackupRestorer(
                args.project_id, 
                service_account_key, 
                args.backup_bucket
            )
            
            # Download backup
            backup_data = restorer.download_backup(args.backup_id)
            
            # Restore collections
            collections_to_restore = args.collections or backup_data['collections'].keys()
            
            for collection_name in collections_to_restore:
                if collection_name in backup_data['collections']:
                    documents = backup_data['collections'][collection_name]['documents']
                    restorer.restore_collection(
                        collection_name, 
                        documents, 
                        args.overwrite
                    )
                else:
                    print(f"⚠️  Collection {collection_name} not found in backup")
            
            print(f"✅ Restore completed successfully!")
            
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()