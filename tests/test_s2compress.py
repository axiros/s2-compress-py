"""s2compress: round trips, the size limit, errors, and blocks written by Go's
klauspost/compress/s2 (tests/data/go-s2.json, made by tests/go-vector)."""

import base64
import json
import os
import threading
from pathlib import Path

import pytest

import s2compress
from s2compress import S2Error, compress, decoded_len, decompress

GO = {name: {k: base64.b64decode(v or "") for k, v in e.items()}
      for name, e in json.loads((Path(__file__).parent / "data" / "go-s2.json").read_text()).items()}


@pytest.mark.parametrize("name", sorted(GO))
def test_blocks_written_by_go_decode(name):
    e = GO[name]
    assert decompress(e["encode"]) == e["payload"]
    assert decompress(e["better"]) == e["payload"], "EncodeBetter output too"
    assert decoded_len(e["encode"]) == len(e["payload"])


@pytest.mark.parametrize("name", sorted(GO))
def test_our_blocks_have_go_sizes(name):
    """minlz encodes like Go's s2.Encode: the same size, within a few bytes"""
    e = GO[name]
    ours = compress(e["payload"])
    assert decompress(ours) == e["payload"]
    assert abs(len(ours) - len(e["encode"])) <= max(16, len(e["encode"]) // 50), (len(ours), len(e["encode"]))


@pytest.mark.parametrize("size", [0, 1, 7, 100, 4096, 65536, 1 << 20])
def test_round_trip(size):
    data = (b"Device.WiFi.Radio.1.Channel=36;" * (size // 31 + 1))[:size]
    out = compress(data)
    assert decompress(out) == data
    if size >= 4096:
        assert len(out) < len(data) / 4, "repetitive data compresses"


def test_random_data_grows_only_a_little():
    data = os.urandom(65536)
    out = compress(data)
    assert len(out) <= len(data) + 32
    assert decompress(out) == data


def test_max_size_is_checked_before_decoding():
    out = compress(b"a" * 100_000)
    with pytest.raises(S2Error, match="more than max_size"):
        decompress(out, max_size=99_999)
    assert decompress(out, max_size=100_000) == b"a" * 100_000
    assert s2compress.DEFAULT_MAX == 64 << 20


def test_broken_input_is_an_error():
    with pytest.raises(S2Error):
        decompress(b"\xff\xff\xff\xff\xff\xff")
    good = compress(b"x" * 5000)
    with pytest.raises(S2Error):
        decompress(good[:-3])
    with pytest.raises(S2Error):
        decoded_len(b"")
    assert issubclass(S2Error, ValueError)
    with pytest.raises(TypeError):
        compress("text, not bytes")


def test_compress_stops_at_16_mib():
    """minlz 1.2.3 writes broken blocks above about 16.06 MiB; compress refuses before that"""
    assert s2compress.MAX_COMPRESS == 16 << 20
    data = (b"Device.WiFi.Radio.1.Channel=36;" * ((17 << 20) // 31 + 1))
    edge = data[:16 << 20]
    assert decompress(compress(edge), max_size=len(edge)) == edge
    with pytest.raises(S2Error, match="at most"):
        compress(data[:(16 << 20) + 1])


def test_a_large_block_from_go_decodes():
    """Above 16 MiB only the decoder is used: Go's 59 MiB block reads correctly"""
    big = json.loads((Path(__file__).parent / "data" / "go-s2-big.json").read_text())
    pattern = big["pattern"].encode()
    want = (pattern * (big["size"] // len(pattern) + 1))[:big["size"]]
    assert decompress(base64.b64decode(big["encode"]), max_size=big["size"]) == want


def test_the_gil_is_released():
    """The main thread keeps running Python while another thread is inside one long
    decompress call: with the GIL held during the call it could not count at all"""
    data = GO["tr181-64k"]["payload"] * 250  # about 16 MB, one block
    block = compress(data)
    started, done = threading.Event(), threading.Event()
    failed = []

    def work():
        started.set()
        try:
            for _ in range(5):
                decompress(block, max_size=len(data))
        except Exception as e:  # noqa: BLE001 - reported below
            failed.append(e)
        finally:
            done.set()

    t = threading.Thread(target=work)
    t.start()
    started.wait()
    counted = 0
    while not done.wait(0) and counted < 10**9:
        counted += 1
    t.join()
    assert not failed, failed
    assert counted > 1000, counted
