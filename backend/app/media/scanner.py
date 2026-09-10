from typing import Protocol
import structlog
import os

logger = structlog.get_logger(__name__)

class VirusScanner(Protocol):
    def scan_file(self, file_path: str) -> bool:
        ...

class ClamAVScanner(VirusScanner):
    def scan_file(self, file_path: str) -> bool:
        logger.info("Mock ClamAV scanning file", path=file_path)
        # Mock logic: if file contains 'EICAR', fail. Otherwise, pass.
        try:
            with open(file_path, 'rb') as f:
                content = f.read(1024)
                if b'EICAR' in content:
                    logger.warning("Virus detected!")
                    return False
            return True
        except Exception:
            return False

def get_scanner() -> VirusScanner:
    return ClamAVScanner()
