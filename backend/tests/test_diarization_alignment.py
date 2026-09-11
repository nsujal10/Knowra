import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from app.ai.diarization.alignment.engine import TemporalAlignmentEngine, AlignmentStatus
from app.ai.diarization.schemas import DiarizationSegment


class TestDiarizationAlignment(unittest.TestCase):
    def setUp(self):
        self.alignment_engine = TemporalAlignmentEngine(
            min_attributed_threshold=0.5,
            overlapping_threshold=0.3,
            ambiguity_margin=0.15,
        )

    def test_alignment_attributed_single_speaker(self):
        """Scenario 1: Single dominant speaker matching ASR interval cleanly."""
        diarization_segments = [
            DiarizationSegment(speaker_label="SPEAKER_00", start_seconds=0.0, end_seconds=2.0),
        ]

        result = self.alignment_engine.align_segment(
            asr_start=0.0,
            asr_end=2.0,
            diarization_segments=diarization_segments,
        )

        self.assertEqual(result.alignment_status, AlignmentStatus.ATTRIBUTED.value)
        self.assertEqual(result.speaker_label, "SPEAKER_00")
        self.assertEqual(result.alignment_confidence, 1.0)
        self.assertEqual(result.overlap_ratio, 1.0)

    def test_alignment_attributed_partial_dominant(self):
        """Scenario 2: Dominant speaker has 75% overlap with ASR segment."""
        diarization_segments = [
            DiarizationSegment(speaker_label="SPEAKER_01", start_seconds=0.5, end_seconds=2.0),
        ]

        result = self.alignment_engine.align_segment(
            asr_start=0.0,
            asr_end=2.0,
            diarization_segments=diarization_segments,
        )

        self.assertEqual(result.alignment_status, AlignmentStatus.ATTRIBUTED.value)
        self.assertEqual(result.speaker_label, "SPEAKER_01")
        self.assertEqual(result.overlap_ratio, 0.75)
        self.assertEqual(result.alignment_confidence, 0.75)

    def test_alignment_overlapping_speakers(self):
        """Scenario 3: Two speakers overlapping simultaneously with substantial coverage."""
        diarization_segments = [
            DiarizationSegment(speaker_label="SPEAKER_00", start_seconds=0.0, end_seconds=1.4),  # 1.4s / 2.0s = 0.7
            DiarizationSegment(speaker_label="SPEAKER_01", start_seconds=0.8, end_seconds=2.0),  # 1.2s / 2.0s = 0.6
        ]

        result = self.alignment_engine.align_segment(
            asr_start=0.0,
            asr_end=2.0,
            diarization_segments=diarization_segments,
        )

        self.assertEqual(result.alignment_status, AlignmentStatus.OVERLAPPING.value)
        self.assertEqual(result.speaker_label, "SPEAKER_00")
        self.assertEqual(result.overlap_ratio, 0.7)
        self.assertEqual(result.alignment_confidence, 0.7)

    def test_alignment_ambiguous_speakers(self):
        """Scenario 4: Two speakers split the duration evenly, neither dominating."""
        diarization_segments = [
            DiarizationSegment(speaker_label="SPEAKER_00", start_seconds=0.0, end_seconds=0.7),  # 0.7 / 2.0 = 0.35
            DiarizationSegment(speaker_label="SPEAKER_01", start_seconds=1.3, end_seconds=2.0),  # 0.7 / 2.0 = 0.35
        ]

        result = self.alignment_engine.align_segment(
            asr_start=0.0,
            asr_end=2.0,
            diarization_segments=diarization_segments,
        )

        self.assertEqual(result.alignment_status, AlignmentStatus.AMBIGUOUS.value)
        self.assertEqual(result.overlap_ratio, 0.35)

    def test_alignment_unattributed_silence(self):
        """Scenario 5: No speaker talking during this ASR segment."""
        diarization_segments = [
            DiarizationSegment(speaker_label="SPEAKER_00", start_seconds=5.0, end_seconds=8.0),
        ]

        result = self.alignment_engine.align_segment(
            asr_start=0.0,
            asr_end=2.0,
            diarization_segments=diarization_segments,
        )

        self.assertEqual(result.alignment_status, AlignmentStatus.UNATTRIBUTED.value)
        self.assertIsNone(result.speaker_label)
        self.assertEqual(result.alignment_confidence, 0.0)
        self.assertEqual(result.overlap_ratio, 0.0)


if __name__ == "__main__":
    unittest.main()
