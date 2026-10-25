"""Tests for plan schema loading, migration, and validation."""
import json
import tempfile
from pathlib import Path

import pytest

from voiceover_edit.plan import CutPlan, EditPlan, WordsData


def _write_json(data):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(data, f)
    f.close()
    return f.name


class TestCutPlanMigration:
    def test_single_input_migrates(self):
        plan = CutPlan.from_dict({
            "input": "video.mov",
            "keep": [[0.0, 3.5], [5.0, 8.2]],
        })
        assert plan.inputs == ["video.mov"]
        assert len(plan.keep) == 1
        assert plan.keep[0] == [[0.0, 3.5], [5.0, 8.2]]

    def test_multi_input(self):
        plan = CutPlan.from_dict({
            "inputs": ["a.mov", "b.mov"],
            "keep": [[[0, 3]], [[1, 5], [7, 9]]],
        })
        assert len(plan.inputs) == 2
        assert plan.flat_clips(1) == [(1, 5), (7, 9)]

    def test_from_file(self):
        path = _write_json({
            "input": "x.mov",
            "keep": [[0, 5], [7, 10]],
        })
        plan = CutPlan.from_file(path)
        assert plan.inputs == ["x.mov"]
        Path(path).unlink()


class TestCutPlanValidation:
    def test_valid_plan(self):
        plan = CutPlan(inputs=["x.mov"], keep=[[[0, 3], [5, 8]]])
        plan.validate()

    def test_overlapping_segments_fail(self):
        plan = CutPlan(inputs=["x.mov"], keep=[[[0, 5], [3, 8]]])
        with pytest.raises(ValueError, match="overlaps"):
            plan.validate()

    def test_end_before_start_fail(self):
        plan = CutPlan(inputs=["x.mov"], keep=[[[5, 3]]])
        with pytest.raises(ValueError, match="end <= start"):
            plan.validate()


class TestEditPlan:
    def test_single_input_migration(self):
        ep = EditPlan.from_dict({
            "input": "a.mov",
            "keep": [[0, 3], [5, 8]],
            "hdr": True,
            "astream": "1",
        })
        assert ep.inputs == ["a.mov"]
        assert ep.tonemap is True
        assert ep.audio_stream == "1"

    def test_defaults(self):
        ep = EditPlan.from_dict({"inputs": ["x.mov"], "keep": []})
        assert ep.crf == 17
        assert ep.preset == "slow"
        assert ep.tonemap_op == "hable"


class TestWordsData:
    def test_s_e_w_migration(self):
        wd = WordsData.from_dict({
            "duration": 10.0,
            "words": [{"s": 0.1, "e": 0.5, "w": "hello"}],
        })
        assert wd.words[0] == {"start": 0.1, "end": 0.5, "word": "hello"}

    def test_start_end_word_preserved(self):
        wd = WordsData.from_dict({
            "duration": 10.0,
            "words": [{"start": 0.1, "end": 0.5, "word": "hello"}],
        })
        assert wd.words[0]["word"] == "hello"

    def test_validation_missing_key(self):
        wd = WordsData(duration=10.0, segments=[], words=[{"start": 0.1}])
        with pytest.raises(ValueError, match="missing"):
            wd.validate()
