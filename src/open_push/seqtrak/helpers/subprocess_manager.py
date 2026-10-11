"""
Subprocess manager for System Settings Mode.

Handles alsaloop process management for iPad audio routing:
- Start/stop iPad → Seqtrak audio routing
- Start/stop Seqtrak → iPad audio routing
- Process status checking
- Graceful error handling
"""

import subprocess
import time


class SubprocessManager:
    """
    Manage system subprocesses for audio routing.

    Tracks alsaloop processes for bidirectional audio between iPad and Seqtrak.
    Prevents duplicate processes and provides status checking.
    """

    def __init__(self):
        """Initialize subprocess manager."""
        self.processes = {}  # {direction_name: subprocess.Popen object}
        self.start_times = {}  # {direction_name: start timestamp}

    def start_alsaloop(self, direction):
        """
        Start alsaloop audio routing in specified direction.

        Args:
            direction: 'ipad_to_seqtrak' or 'seqtrak_to_ipad'

        Returns:
            tuple: (success: bool, message: str)
        """
        # Check if already running
        if self.is_running(direction):
            return False, "Already running"

        # Build alsaloop command based on direction
        if direction == 'ipad_to_seqtrak':
            # iPad (card 0) → Seqtrak (card 5)
            cmd = ['alsaloop', '-C', 'plughw:0,0', '-P', 'plughw:5,0', '-t', '50000', '-d']
        elif direction == 'seqtrak_to_ipad':
            # Seqtrak (card 5) → iPad (card 0)
            cmd = ['alsaloop', '-C', 'plughw:5,0', '-P', 'plughw:0,0', '-t', '50000', '-d']
        else:
            return False, "Invalid direction"

        # Start process
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes[direction] = proc
            self.start_times[direction] = time.time()
            return True, "Started"
        except FileNotFoundError:
            return False, "alsaloop not found"
        except PermissionError:
            return False, "Permission denied"
        except Exception as e:
            return False, f"Error: {str(e)[:20]}"

    def stop(self, direction):
        """
        Stop alsaloop process for specified direction.

        Args:
            direction: 'ipad_to_seqtrak' or 'seqtrak_to_ipad'

        Returns:
            tuple: (success: bool, message: str)
        """
        if direction not in self.processes:
            return False, "Not running"

        proc = self.processes[direction]

        # Check if process is still alive
        if proc.poll() is not None:
            # Process already terminated
            del self.processes[direction]
            if direction in self.start_times:
                del self.start_times[direction]
            return False, "Already stopped"

        # Terminate process
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            # Force kill if terminate didn't work
            proc.kill()
            proc.wait()

        # Cleanup
        del self.processes[direction]
        if direction in self.start_times:
            del self.start_times[direction]

        return True, "Stopped"

    def is_running(self, direction):
        """
        Check if alsaloop process is running for specified direction.

        Args:
            direction: 'ipad_to_seqtrak' or 'seqtrak_to_ipad'

        Returns:
            bool: True if process is running, False otherwise
        """
        if direction not in self.processes:
            return False

        proc = self.processes[direction]

        # Check if process is still alive
        if proc.poll() is None:
            return True

        # Process died, cleanup
        del self.processes[direction]
        if direction in self.start_times:
            del self.start_times[direction]
        return False

    def get_status(self, direction):
        """
        Get status string for specified direction.

        Args:
            direction: 'ipad_to_seqtrak' or 'seqtrak_to_ipad'

        Returns:
            str: Status message (e.g., "Active", "Inactive", "Waiting")
        """
        if not self.is_running(direction):
            return "Inactive"

        # Calculate uptime
        if direction in self.start_times:
            uptime = int(time.time() - self.start_times[direction])
            if uptime < 60:
                return f"Active {uptime}s"
            else:
                mins = uptime // 60
                return f"Active {mins}m"

        return "Active"

    def stop_all(self):
        """
        Stop all running alsaloop processes.

        Returns:
            int: Number of processes stopped
        """
        count = 0
        directions = list(self.processes.keys())  # Copy keys to avoid dict change during iteration

        for direction in directions:
            success, _ = self.stop(direction)
            if success:
                count += 1

        return count

    def cleanup(self):
        """Cleanup all processes (called on exit)."""
        self.stop_all()
