import os
import re
from datetime import datetime

class DVRScanner:
    def __init__(self, directory_path):
        self.directory_path = directory_path
        # Example: NOR_20260307_174045_F.mp4
        self.filename_pattern = re.compile(r'^NOR_(\d{8})_(\d{6})_([FBLRS])\.mp4$')
        
    def scan_and_group(self):
        """
        Scans the directory and returns a sorted list of dictionaries.
        Each dictionary represents a timestamp group containing available video angles.
        
        Returns:
            list: [{'timestamp': datetime_obj, 'timestamp_str': '20260307_174045', 'angles': {'F': 'path', 'B': 'path', ...}}, ...]
        """
        if not os.path.exists(self.directory_path):
            print(f"Error: Directory {self.directory_path} does not exist.")
            return []

        # Dictionary to group files by their timestamp string (e.g., "20260307_174045")
        groups = {}

        for filename in os.listdir(self.directory_path):
            # Skip hidden files that start with ._ (macOS specific)
            if filename.startswith('._'):
                continue
                
            match = self.filename_pattern.match(filename)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                angle = match.group(3)
                
                timestamp_str = f"{date_str}_{time_str}"
                full_path = os.path.join(self.directory_path, filename)
                
                if timestamp_str not in groups:
                    # Convert string to datetime for accurate chronological sorting
                    try:
                        dt_obj = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    except ValueError:
                        print(f"Warning: Discovered invalid date format in {filename}")
                        continue
                        
                    groups[timestamp_str] = {
                        'timestamp': dt_obj,
                        'timestamp_str': timestamp_str,
                        'angles': {}
                    }
                
                groups[timestamp_str]['angles'][angle] = full_path

        # Convert dictionary to list and sort by datetime
        sorted_groups = list(groups.values())
        sorted_groups.sort(key=lambda x: x['timestamp'])
        
        return sorted_groups

if __name__ == '__main__':
    # Simple test
    test_dir = '/Volumes/Untitled/DVR/NOR'
    scanner = DVRScanner(test_dir)
    results = scanner.scan_and_group()
    print(f"Found {len(results)} distinct time groups.")
    if results:
        print(f"First group: {results[0]['timestamp_str']} - Angles: {list(results[0]['angles'].keys())}")
        print(f"Last group: {results[-1]['timestamp_str']} - Angles: {list(results[-1]['angles'].keys())}")
