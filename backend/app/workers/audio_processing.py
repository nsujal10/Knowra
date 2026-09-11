from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.media_asset import MediaAsset
from app.models.media_artifact import MediaArtifact
from app.models.processing_job import ProcessingJob
from app.models.audio_enums import AudioProcessingStatus
from app.storage.minio import get_storage_client
from app.storage.service import StorageService

from app.media.audio.validator import validate_audio
from app.media.audio.analyzer import analyze_audio
from app.media.audio.normalizer import normalize_to_canonical
from app.media.ffmpeg.errors import EmptyAudio, CorruptedAudio, DecodeFailure, FFmpegTimeout

import structlog
import tempfile
import os
import shutil
import time
from uuid import UUID

logger = structlog.get_logger(__name__)

def update_job_stage(db, job: ProcessingJob, stage: AudioProcessingStatus, error_msg: str = None):
    job.job_stage = stage.value
    if error_msg:
        job.error_message = error_msg
        job.status = "FAILED"
    db.commit()

@celery_app.task(bind=True, max_retries=3)
def audio_processing_task(self, job_id: str, tenant_id: str, media_id: str):
    start_time = time.time()
    log = logger.bind(job_id=job_id, tenant_id=tenant_id, media_id=media_id)
    log.info("Starting Enterprise Audio Processing Pipeline")
    
    db = SessionLocal()
    storage = get_storage_client()
    workspace_dir = f"/tmp/knowra/{job_id}/"
    
    try:
        # 1. Tenant Isolation Validation
        media = db.query(MediaAsset).filter(MediaAsset.id == UUID(media_id)).first()
        job = db.query(ProcessingJob).filter(ProcessingJob.id == UUID(job_id)).first()
        
        if not media or not job:
            raise ValueError("MediaAsset or ProcessingJob not found.")
            
        if str(media.tenant_id) != tenant_id or str(job.tenant_id) != tenant_id:
            log.error("Tenant isolation breach detected! Aborting.")
            raise ValueError("Tenant isolation validation failed.")
            
        # 2. Workspace Setup
        os.makedirs(workspace_dir, exist_ok=True)
        local_source = os.path.join(workspace_dir, "source_media")
        local_normalized = os.path.join(workspace_dir, "normalized.wav")
        
        # 3. Download Source
        update_job_stage(db, job, AudioProcessingStatus.AUDIO_EXTRACTING)
        storage.download_file("knowra-raw", media.storage_key, local_source)
        
        # 4. Validation & Extraction
        duration = validate_audio(local_source)
        log.info("Audio validated", duration_seconds=duration)
        
        # 5. Analysis
        update_job_stage(db, job, AudioProcessingStatus.AUDIO_ANALYZING)
        analysis = analyze_audio(local_source, duration)
        log.info("Audio analyzed", quality=analysis.quality.value, silence_ratio=analysis.silence_duration/duration)
        
        # 6. Normalization
        update_job_stage(db, job, AudioProcessingStatus.AUDIO_NORMALIZING)
        norm_meta = normalize_to_canonical(local_source, local_normalized)
        
        # 7. Upload Artifact
        derived_key = StorageService.generate_derived_key(UUID(tenant_id), media.meeting_id, media.id, "16khz_mono", "wav")
        storage.upload_file("knowra-derived", derived_key, local_normalized, "audio/wav")
        
        # 8. Transactional Database Update
        artifact = MediaArtifact(
            tenant_id=media.tenant_id,
            media_asset_id=media.id,
            artifact_type="NORMALIZED_AUDIO",
            storage_bucket="knowra-derived",
            storage_key=derived_key,
            checksum_sha256=norm_meta["checksum_sha256"],
            duration_seconds=duration,
            sample_rate=norm_meta["sample_rate"],
            channels=norm_meta["channels"],
            sample_format=norm_meta["sample_format"],
            byte_size=norm_meta["byte_size"]
        )
        db.add(artifact)
        
        job.job_stage = AudioProcessingStatus.READY_FOR_TRANSCRIPTION.value
        job.status = "COMPLETED"
        job.metadata_json = {
            "quality": analysis.quality.value,
            "processing_seconds": round(time.time() - start_time, 2)
        }
        db.commit()
        
        log.info("Audio processing pipeline completed successfully", processing_seconds=job.metadata_json["processing_seconds"])
        
    except EmptyAudio as e:
        update_job_stage(db, job, AudioProcessingStatus.EMPTY_AUDIO, str(e))
    except CorruptedAudio as e:
        update_job_stage(db, job, AudioProcessingStatus.AUDIO_CORRUPTED, str(e))
    except (DecodeFailure, FFmpegTimeout) as e:
        log.warning("Transient FFmpeg error, initiating retry", error=str(e))
        db.close() # Close session before retrying
        raise self.retry(exc=e, countdown=15)
    except Exception as e:
        update_job_stage(db, job, AudioProcessingStatus.FAILED, str(e))
        log.error("Pipeline failed fatally", error=str(e))
    finally:
        # Guarantee cleanup regardless of success, failure, or timeout
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir)
        if db:
            db.close()
