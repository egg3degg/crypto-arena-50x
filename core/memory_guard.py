"""
Memory Guard & Defragmentation Module
Prevents memory leaks and Linux glibc heap fragmentation on Render (512MB RAM limit).
Periodically invokes gc.collect() and libc malloc_trim(0) to release freed heap pages back to the OS.
"""
import os
import sys
import gc
import time
import logging
import asyncio
from typing import Optional, Any

logger = logging.getLogger("CryptoArena.MemoryGuard")

# Pre-load libc on Linux for fast malloc_trim calls
_libc = None
if sys.platform.startswith("linux"):
    try:
        import ctypes
        _libc = ctypes.CDLL("libc.so.6")
    except Exception as e:
        logger.warning(f"Could not load libc.so.6 for malloc_trim: {e}")


def get_process_rss_mb() -> float:
    """Returns current process Resident Set Size (RSS) in Megabytes."""
    # 1. Linux cgroup / procfs (most accurate on Render/Docker)
    if os.path.exists("/proc/self/status"):
        try:
            with open("/proc/self/status", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        # VmRSS is in kB, e.g. 'VmRSS:   123456 kB'
                        parts = line.split()
                        return round(float(parts[1]) / 1024.0, 2)
        except Exception:
            pass

    # 2. Python resource module (Unix/macOS)
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux ru_maxrss is in kB; on macOS it is in bytes
        if sys.platform == "darwin":
            return round(usage / (1024.0 * 1024.0), 2)
        return round(usage / 1024.0, 2)
    except Exception:
        pass

    # 3. Fallback on Windows
    return 0.0


def trim_memory() -> float:
    """
    Executes garbage collection and releases freed heap memory back to the OS.
    Returns the current RSS in MB after trimming.
    """
    # Force full Python generational garbage collection
    gc.collect()

    # On Linux glibc, force heap trimming back to the kernel
    if _libc is not None and hasattr(_libc, "malloc_trim"):
        try:
            _libc.malloc_trim(0)
        except Exception:
            pass

    return get_process_rss_mb()


class MemoryGuard:
    def __init__(self, engine: Optional[Any] = None, check_interval: int = 60, emergency_limit_mb: float = 320.0):
        self.engine = engine
        self.check_interval = check_interval
        self.emergency_limit_mb = emergency_limit_mb
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def run_loop(self):
        """Asynchronous background loop monitoring and managing memory."""
        self.is_running = True
        logger.info(f"🛡️ Memory Guard active (Interval: {self.check_interval}s, Emergency Ceiling: {self.emergency_limit_mb}MB)")

        while self.is_running:
            try:
                await asyncio.sleep(self.check_interval)
                rss_before = get_process_rss_mb()
                rss_after = trim_memory()

                # Periodic database snapshot pruning
                if self.engine and hasattr(self.engine, "db") and self.engine.db:
                    try:
                        self.engine.db.prune_old_snapshots(keep_latest=2000)
                    except Exception as dbe:
                        logger.debug(f"DB snapshot pruning notice: {dbe}")

                # Emergency purge if memory approaches 512MB limit
                if rss_after >= self.emergency_limit_mb:
                    logger.warning(
                        f"⚠️ [MEMORY CEILING ALERT] RSS is {rss_after:.1f} MB (Ceiling: {self.emergency_limit_mb} MB). "
                        "Executing emergency cache flush and heap compaction..."
                    )
                    if self.engine and hasattr(self.engine, "market_feed") and self.engine.market_feed:
                        if hasattr(self.engine.market_feed, "clear_cache"):
                            self.engine.market_feed.clear_cache()

                    # Full GC and trim
                    gc.collect(2)
                    rss_after = trim_memory()
                    logger.info(f"✔ Emergency memory flush complete. RSS now: {rss_after:.1f} MB")
                elif rss_before > 0:
                    logger.debug(f"Memory Guard tick: RSS {rss_after:.1f} MB (trimmed from {rss_before:.1f} MB)")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in MemoryGuard loop: {e}", exc_info=False)

    def start(self) -> asyncio.Task:
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self.run_loop())
        return self._task

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
