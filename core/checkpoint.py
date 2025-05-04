"""Checkpoint system for RetroClamp.

This module provides functionality for saving and restoring the state of
long-running operations, allowing for pause and resume capabilities.
"""

import os
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime

from PySide6.QtCore import QObject, Signal


@dataclass
class BatchItem:
    """Represents an item in a batch operation.
    
    Attributes:
        id: Unique identifier for the item
        input_path: Path to the input file
        output_path: Path to the output file
        operation: Operation to perform (e.g., 'createcd', 'extractcd')
        status: Current status of the item ('pending', 'in_progress', 'completed', 'failed')
        progress: Progress percentage (0-100)
        error: Error message if status is 'failed'
        start_time: Time when processing started
        end_time: Time when processing completed or failed
        parameters: Additional operation-specific parameters
    """
    id: str
    input_path: str
    output_path: str
    operation: str
    status: str = "pending"
    progress: float = 0.0
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Checkpoint:
    """Represents a checkpoint for a batch operation.
    
    Attributes:
        id: Unique identifier for the checkpoint
        name: Human-readable name for the checkpoint
        items: List of batch items
        current_index: Index of the current item being processed
        created_at: Time when the checkpoint was created
        updated_at: Time when the checkpoint was last updated
        completed_count: Number of completed items
        failed_count: Number of failed items
        total_count: Total number of items
    """
    id: str
    name: str
    items: List[BatchItem]
    current_index: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_count: int = 0
    failed_count: int = 0
    total_count: int = 0


class CheckpointSignals(QObject):
    """Signals for checkpoint operations.
    
    Signals:
        saved: Emitted when a checkpoint is saved
        loaded: Emitted when a checkpoint is loaded
        updated: Emitted when a checkpoint is updated
        error: Emitted when an error occurs
    """
    saved = Signal(str)  # Checkpoint ID
    loaded = Signal(str)  # Checkpoint ID
    updated = Signal(str)  # Checkpoint ID
    error = Signal(str)  # Error message


class CheckpointManager:
    """Manager for checkpoint operations.
    
    This class provides functionality for creating, saving, loading, and
    updating checkpoints for batch operations.
    """
    
    def __init__(self, checkpoint_dir: str = None):
        """Initialize the CheckpointManager.
        
        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = checkpoint_dir or os.path.join(os.path.expanduser("~"), ".retroclamp", "checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.signals = CheckpointSignals()
        self.current_checkpoint: Optional[Checkpoint] = None
    
    def create_checkpoint(self, name: str, items: List[BatchItem]) -> Checkpoint:
        """Create a new checkpoint.
        
        Args:
            name: Human-readable name for the checkpoint
            items: List of batch items
            
        Returns:
            Newly created checkpoint
        """
        checkpoint_id = str(uuid.uuid4())
        checkpoint = Checkpoint(
            id=checkpoint_id,
            name=name,
            items=items,
            current_index=0,
            created_at=time.time(),
            updated_at=time.time(),
            completed_count=0,
            failed_count=0,
            total_count=len(items)
        )
        
        self.current_checkpoint = checkpoint
        self._save_checkpoint(checkpoint)
        self.signals.saved.emit(checkpoint_id)
        
        return checkpoint
    
    def save_checkpoint(self) -> bool:
        """Save the current checkpoint.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.current_checkpoint:
            self.signals.error.emit("No current checkpoint to save")
            return False
        
        self.current_checkpoint.updated_at = time.time()
        self._save_checkpoint(self.current_checkpoint)
        self.signals.updated.emit(self.current_checkpoint.id)
        
        return True
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load a checkpoint by ID.
        
        Args:
            checkpoint_id: ID of the checkpoint to load
            
        Returns:
            Loaded checkpoint or None if not found
        """
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        
        if not os.path.exists(checkpoint_path):
            self.signals.error.emit(f"Checkpoint not found: {checkpoint_id}")
            return None
        
        try:
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
                
            # Convert plain dict to BatchItem objects
            items = []
            for item_data in data.get("items", []):
                items.append(BatchItem(**item_data))
                
            # Create checkpoint object
            checkpoint = Checkpoint(
                id=data.get("id"),
                name=data.get("name"),
                items=items,
                current_index=data.get("current_index", 0),
                created_at=data.get("created_at", time.time()),
                updated_at=data.get("updated_at", time.time()),
                completed_count=data.get("completed_count", 0),
                failed_count=data.get("failed_count", 0),
                total_count=data.get("total_count", len(items))
            )
            
            self.current_checkpoint = checkpoint
            self.signals.loaded.emit(checkpoint_id)
            
            return checkpoint
            
        except Exception as e:
            self.signals.error.emit(f"Error loading checkpoint: {str(e)}")
            return None
    
    def update_item(self, item_id: str, **updates) -> bool:
        """Update a batch item in the current checkpoint.
        
        Args:
            item_id: ID of the item to update
            **updates: Attributes to update
            
        Returns:
            True if successful, False otherwise
        """
        if not self.current_checkpoint:
            self.signals.error.emit("No current checkpoint")
            return False
        
        # Find the item by ID
        for item in self.current_checkpoint.items:
            if item.id == item_id:
                # Update the item attributes
                for key, value in updates.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                
                # Update checkpoint stats
                self._update_checkpoint_stats()
                
                # Save the updated checkpoint
                self.save_checkpoint()
                return True
        
        self.signals.error.emit(f"Item not found: {item_id}")
        return False
    
    def get_next_pending_item(self) -> Optional[BatchItem]:
        """Get the next pending item from the current checkpoint.
        
        Returns:
            Next pending item or None if no pending items
        """
        if not self.current_checkpoint:
            return None
        
        # Start from the current index
        for i in range(self.current_checkpoint.current_index, len(self.current_checkpoint.items)):
            item = self.current_checkpoint.items[i]
            if item.status == "pending":
                self.current_checkpoint.current_index = i
                return item
        
        # If no pending items found from current index, check from the beginning
        for i in range(0, self.current_checkpoint.current_index):
            item = self.current_checkpoint.items[i]
            if item.status == "pending":
                self.current_checkpoint.current_index = i
                return item
        
        return None
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints.
        
        Returns:
            List of checkpoint metadata (id, name, created_at, updated_at, progress)
        """
        checkpoints = []
        
        for filename in os.listdir(self.checkpoint_dir):
            if filename.endswith(".json"):
                try:
                    checkpoint_path = os.path.join(self.checkpoint_dir, filename)
                    with open(checkpoint_path, 'r') as f:
                        data = json.load(f)
                        
                    # Calculate progress
                    total = data.get("total_count", 0)
                    completed = data.get("completed_count", 0)
                    progress = (completed / total) * 100 if total > 0 else 0
                    
                    checkpoints.append({
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "progress": progress,
                        "total_count": total,
                        "completed_count": completed,
                        "failed_count": data.get("failed_count", 0)
                    })
                except Exception:
                    # Skip invalid checkpoint files
                    pass
        
        # Sort by updated_at (newest first)
        checkpoints.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
        
        return checkpoints
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: ID of the checkpoint to delete
            
        Returns:
            True if successful, False otherwise
        """
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
        
        if not os.path.exists(checkpoint_path):
            self.signals.error.emit(f"Checkpoint not found: {checkpoint_id}")
            return False
        
        try:
            os.remove(checkpoint_path)
            
            # If this was the current checkpoint, clear it
            if self.current_checkpoint and self.current_checkpoint.id == checkpoint_id:
                self.current_checkpoint = None
                
            return True
        except Exception as e:
            self.signals.error.emit(f"Error deleting checkpoint: {str(e)}")
            return False
    
    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save a checkpoint to disk.
        
        Args:
            checkpoint: Checkpoint to save
        """
        checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint.id}.json")
        
        # Convert to dict for JSON serialization
        data = asdict(checkpoint)
        
        with open(checkpoint_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _update_checkpoint_stats(self) -> None:
        """Update the statistics of the current checkpoint."""
        if not self.current_checkpoint:
            return
        
        completed_count = 0
        failed_count = 0
        
        for item in self.current_checkpoint.items:
            if item.status == "completed":
                completed_count += 1
            elif item.status == "failed":
                failed_count += 1
        
        self.current_checkpoint.completed_count = completed_count
        self.current_checkpoint.failed_count = failed_count
        self.current_checkpoint.updated_at = time.time()
    
    @staticmethod
    def format_timestamp(timestamp: float) -> str:
        """Format a timestamp as a human-readable string.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            Formatted date and time string
        """
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
