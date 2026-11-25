import pytest

from maquina.captions import chunk_words, time_words, to_ass, to_srt
from maquina.models import Word


def W(t, s, e):
    return Word(t, s, e)


def test_time_words_uses_whisper_times_when_tokens_match():
    whisper = [W("olha", 0.2, 0.5), W("o", 0.5, 0.6), W("que", 0.6, 0.9)]
    out = time_words(["Olha", "o", "que"], ["olha", "o", "que"], whisper, (0.0, 1.0))
    assert [(w.text, w.start) for w in out] == [("Olha", 0.2), ("o", 0.5), ("que", 0.6)]


def test_time_words_interpolates_missing_token():
    whisper = [W("olha", 0.0, 0.3), W("que", 0.9, 1.2)]
    out = time_words(["olha", "isso", "que"], ["olha", "isso", "que"], whisper, (0.0, 1.2))
    assert out[0].start == 0.0 and out[2].start == 0.9
    assert 0.0 < out[1].start < 0.9


def test_time_words_when_display_has_fewer_tokens_than_spoken():
    # display "NS61" is spoken as "n s sessenta e um"
    spoken = ["esse", "é", "o", "n", "s", "sessenta", "e", "um"]
    whisper = [W(t, i * 0.25, i * 0.25 + 0.2) for i, t in enumerate(spoken)]
    out = time_words(["Esse", "é", "o", "NS61"], spoken, whisper, (0.0, 2.0))
    assert len(out) == 4
    assert [w.start for w in out] == sorted(w.start for w in out)
    assert out[-1].start >= 0.75


def test_times_are_monotonic_and_end_after_start():
    out = time_words(["a", "b", "c"], ["a", "b", "c"], [], (1.0, 4.0))
    assert all(w.end > w.start for w in out)
    assert [w.start for w in out] == sorted(w.start for w in out)
    assert out[0].start >= 1.0 and out[-1].end <= 4.0 + 1e-6


def test_chunk_words_respects_max_words_and_punctuation():
    words = [W(t, i * 0.3, i * 0.3 + 0.25) for i, t in enumerate(
        ["Ainda", "joga", "com", "teclado", "de", "membrana?", "Olha", "isso"])]
    chunks = chunk_words(words, max_words=3)
    assert all(len(c) <= 3 for c in chunks)
    assert chunks[1][-1].text == "membrana?" or any(c[-1].text == "membrana?" for c in chunks)


def test_ass_highlights_current_word_and_srt_has_timecodes():
    words = [W("Olha", 0.0, 0.4), W("isso", 0.4, 0.9)]
    ass = to_ass(words, width=1080, height=1920)
    assert "PlayResX: 1080" in ass and "Dialogue:" in ass and "\\c&H" in ass
    assert ass.count("Dialogue:") == 2
    srt = to_srt(words)
    assert "00:00:00,000 --> 00:00:00,900" in srt and "Olha isso" in srt


def test_words_after_a_multi_token_substitution_keep_their_own_times():
    spoken = "hoje está noventa reais e setenta e sete centavos na promoção".split()
    whisper = [W(t, i * 0.3, i * 0.3 + 0.25) for i, t in enumerate(spoken)]
    out = time_words(["Hoje", "está", "R$", "90,77", "na", "promoção"], spoken, whisper, (0.0, 3.3))
    by = {w.text: w.start for w in out}
    assert by["na"] == pytest.approx(9 * 0.3) and by["promoção"] == pytest.approx(10 * 0.3)
    assert by["R$"] == pytest.approx(2 * 0.3)
    assert 2 * 0.3 < by["90,77"] < 9 * 0.3
