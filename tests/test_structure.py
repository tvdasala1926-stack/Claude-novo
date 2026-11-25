import pytest

from maquina.models import Word
from maquina.structure import cuts_per_minute, first_seconds_text, split_structure

NAMES = ["gancho", "introducao", "desenvolvimento", "problema", "virada",
         "climax", "conclusao", "cta"]


def _assert_contiguous(segments, duration):
    assert [s.name for s in segments] == NAMES
    assert segments[0].start == 0
    assert segments[-1].end == pytest.approx(duration)
    for a, b in zip(segments, segments[1:]):
        assert a.end == pytest.approx(b.start)
    assert all(s.start <= s.end for s in segments)


def test_thirty_seconds_without_words_or_cuts():
    segs = split_structure(30.0, [], [])
    _assert_contiguous(segs, 30.0)
    assert segs[0].end == 3.0
    assert segs[-1].start == pytest.approx(25.5)


def test_cta_keyword_in_final_half_sets_cta_start():
    words = [Word("oi", 1.0, 1.3), Word("link", 27.0, 27.4)]
    segs = split_structure(30.0, words, [])
    _assert_contiguous(segs, 30.0)
    assert segs[-1].start == 27.0


def test_cta_keyword_in_first_half_is_ignored():
    segs = split_structure(30.0, [Word("link", 5.0, 5.3)], [])
    assert segs[-1].start == pytest.approx(25.5)


def test_cuts_pull_boundaries():
    segs = split_structure(30.0, [], [8.9])
    _assert_contiguous(segs, 30.0)
    assert 8.9 in [s.start for s in segs]


def test_very_short_video_still_covers_whole_duration():
    _assert_contiguous(split_structure(2.0, [], []), 2.0)


def test_first_seconds_text_only_words_starting_before_cutoff():
    words = [Word("compre", 0.2, 0.6), Word("agora", 2.5, 2.9), Word("depois", 3.1, 3.5)]
    assert first_seconds_text(words) == "compre agora"
    assert first_seconds_text([]) == ""


def test_cuts_per_minute():
    assert cuts_per_minute(30.0, [5, 10, 15]) == 6.0
    assert cuts_per_minute(0, []) == 0.0
