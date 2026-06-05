from collections import deque
from typing import Dict

class TemporalFilter:
    """
    Maintains a rolling window of recent values (e.g., emotions) for each track_id
    to provide temporal smoothing and prevent rapid flickering in the UI.
    """
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.history: Dict[int, deque] = {}

    def update(self, track_id: int, value: str) -> str:
        """
        Adds the latest value to the rolling window for the track_id and returns
        the most frequent value (mode) across the window.
        """
        if track_id is None:
            return value

        if track_id not in self.history:
            self.history[track_id] = deque(maxlen=self.window_size)
            
        self.history[track_id].append(value)
        
        # Calculate the most frequent value (mode)
        counts = {}
        for item in self.history[track_id]:
            counts[item] = counts.get(item, 0) + 1
            
        # Return the item with the highest count
        best_item = max(counts.items(), key=lambda x: x[1])[0]
        return best_item
        
    def cleanup(self, active_track_ids: list[int]):
        """
        Removes track_ids from history that are no longer active to prevent memory leaks.
        """
        ids_to_remove = [tid for tid in self.history.keys() if tid not in active_track_ids]
        for tid in ids_to_remove:
            del self.history[tid]
