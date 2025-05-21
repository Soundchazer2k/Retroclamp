"""
Checkpoint Manager for RetroClamp

Provides functionality to save and restore batch processing state,
allowing for process resumption after interruptions.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

class CheckpointManager:
    """Manages saving and loading of batch processing checkpoints."""
    
    VERSION = 1
    
    def __init__(self, checkpoint_dir: Optional[str] = None):
        """Initialize the CheckpointManager.
        
        Args:
            checkpoint_dir: Directory to store checkpoint files. If None, 
                          uses ~/.retroclamp/checkpoints
        """
        if checkpoint_dir is None:
            checkpoint_dir = os.path.join(
                os.path.expanduser("~"),
                ".retroclamp",
                "checkpoints"
            )
        
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def create_checkpoint(
        self,
        batch_id: str,
        files: List[Dict[str, Any]],
        current_index: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new checkpoint.
        
        Args:
            batch_id: Unique identifier for this batch
            files: List of file dictionaries with at least 'path' and 'status' keys
            current_index: Current processing index
            metadata: Additional metadata to store
            
        Returns:
            Path to the created checkpoint file
        """
        checkpoint = {
            'version': self.VERSION,
            'batch_id': batch_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'current_index': current_index,
            'total_files': len(files),
            'files': files,
            'metadata': metadata or {}
        }
        
        checkpoint_file = os.path.join(
            self.checkpoint_dir,
            f"batch_{batch_id}.json"
        )
        
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)
            self.logger.info(f"Created checkpoint: {checkpoint_file}")
            return checkpoint_file
        except Exception as e:
            self.logger.error(f"Failed to create checkpoint: {e}")
            raise
    
    def load_checkpoint(self, checkpoint_path: str) -> Dict[str, Any]:
        """Load a checkpoint from file.
        
        Args:
            checkpoint_path: Path to the checkpoint file
            
        Returns:
            Dictionary containing the checkpoint data
            
        Raises:
            FileNotFoundError: If checkpoint file doesn't exist
            ValueError: If checkpoint is invalid or version mismatch
        """
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_path}")
            
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            # Validate checkpoint
            if checkpoint.get('version') != self.VERSION:
                raise ValueError(f"Unsupported checkpoint version: {checkpoint.get('version')}")
                
            return checkpoint
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid checkpoint file: {e}") from e
        except Exception as e:
            self.logger.error(f"Error loading checkpoint: {e}")
            raise
    
    def get_latest_checkpoint(self, batch_id: Optional[str] = None) -> Optional[str]:
        """Get the most recent checkpoint file.
        
        Args:
            batch_id: Optional batch ID to filter checkpoints
            
        Returns:
            Path to the latest checkpoint file, or None if none found
        """
        try:
            checkpoints = []
            for f in os.listdir(self.checkpoint_dir):
                if not f.endswith('.json') or not f.startswith('batch_'):
                    continue
                    
                if batch_id and f != f"batch_{batch_id}.json":
                    continue
                    
                path = os.path.join(self.checkpoint_dir, f)
                try:
                    mtime = os.path.getmtime(path)
                    checkpoints.append((mtime, path))
                except (OSError, ValueError):
                    continue
            
            if not checkpoints:
                return None
                
            # Sort by modification time, newest first
            checkpoints.sort(reverse=True, key=lambda x: x[0])
            return checkpoints[0][1]
            
        except Exception as e:
            self.logger.error(f"Error finding checkpoints: {e}")
            return None
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints with their metadata.
        
        Returns:
            List of dictionaries containing checkpoint metadata
        """
        checkpoints = []
        
        try:
            for f in os.listdir(self.checkpoint_dir):
                if not f.endswith('.json') or not f.startswith('batch_'):
                    continue
                    
                path = os.path.join(self.checkpoint_dir, f)
                try:
                    # Load the checkpoint to get its metadata
                    with open(path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                    
                    # Get file stats
                    stat = os.stat(path)
                    
                    checkpoints.append({
                        'filename': f,
                        'path': path,
                        'batch_id': data.get('batch_id', 'unknown'),
                        'timestamp': data.get('timestamp'),
                        'created': stat.st_ctime,
                        'modified': stat.st_mtime,
                        'size': stat.st_size,
                        'current_index': data.get('current_index', 0),
                        'total_files': data.get('total_files', 0),
                        'version': data.get('version', 'unknown')
                    })
                    
                except (json.JSONDecodeError, KeyError, OSError) as e:
                    self.logger.warning(f"Skipping invalid checkpoint {f}: {e}")
                    continue
            
            # Sort by modification time, newest first
            checkpoints.sort(key=lambda x: x['modified'], reverse=True)
            
        except OSError as e:
            self.logger.error(f"Error listing checkpoints: {e}")
            
        return checkpoints
    
    def cleanup_old_checkpoints(self, max_age_days: int = 7) -> int:
        """Remove checkpoint files older than the specified number of days.
        
        Args:
            max_age_days: Maximum age in days to keep checkpoints
            
        Returns:
            Number of checkpoints removed
        """
        removed = 0
        now = datetime.now(timezone.utc).timestamp()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        try:
            for f in os.listdir(self.checkpoint_dir):
                if not f.endswith('.json') or not f.startswith('batch_'):
                    continue
                    
                path = os.path.join(self.checkpoint_dir, f)
                try:
                    mtime = os.path.getmtime(path)
                    if (now - mtime) > max_age_seconds:
                        os.remove(path)
                        removed += 1
                        self.logger.debug(f"Removed old checkpoint: {path}")
                except (OSError, ValueError):
                    continue
                    
            return removed
            
        except Exception as e:
            self.logger.error(f"Error cleaning up checkpoints: {e}")
            return removed
