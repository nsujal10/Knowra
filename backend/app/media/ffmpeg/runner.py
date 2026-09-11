import asyncio
import structlog
from app.media.ffmpeg.errors import FFmpegTimeout, DecodeFailure

logger = structlog.get_logger(__name__)

async def run_command_async(cmd: list[str], timeout: int = 300) -> tuple[str, str]:
    """
    Executes a shell command asynchronously with strict timeouts.
    Never uses shell=True. Commands must be passed as lists.
    """
    logger.info("Executing subprocess", command=cmd[0], args=cmd[1:])
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate() # flush buffers
            logger.error("Subprocess timed out", command=cmd[0], timeout=timeout)
            raise FFmpegTimeout(f"Command '{cmd[0]}' timed out after {timeout} seconds")
            
        if process.returncode != 0:
            err_msg = stderr.decode('utf-8', errors='ignore')
            logger.error("Subprocess failed", command=cmd[0], returncode=process.returncode, stderr=err_msg)
            raise DecodeFailure(f"Command failed with code {process.returncode}: {err_msg}")
            
        return stdout.decode('utf-8', errors='ignore'), stderr.decode('utf-8', errors='ignore')
    except Exception as e:
        if isinstance(e, (FFmpegTimeout, DecodeFailure)):
            raise
        logger.exception("Unexpected subprocess error")
        raise DecodeFailure(f"Unexpected error running command: {str(e)}")

def run_command(cmd: list[str], timeout: int = 300) -> tuple[str, str]:
    """Synchronous wrapper for Celery compatibility."""
    return asyncio.run(run_command_async(cmd, timeout))
