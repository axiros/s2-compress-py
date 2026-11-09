# s2-compress-py

S2 block compression for Python, compatible with Go's
[klauspost/compress/s2](https://github.com/klauspost/compress/tree/master/s2) block format
(`s2.Encode`, `s2.EncodeBetter`, `s2.Decode`). Built in Rust on
[minlz](https://crates.io/crates/minlz). Python 3.11 and later.

## Usage

```python
import s2compress

block = s2compress.compress(data)                    # bytes -> bytes
data = s2compress.decompress(block)                  # refuses blocks above 64 MiB
data = s2compress.decompress(block, max_size=1 << 20)
s2compress.decoded_len(block)                        # size from the block header
```

Errors raise `s2compress.S2Error`, a `ValueError`. `compress` takes at most 16 MiB
(`MAX_COMPRESS`). The GIL is released while data is compressed or decompressed.

## Build

```
uvx maturin build --release
```

## License

Apache-2.0, Copyright 2026 Axiros GmbH. Distributions must carry the attribution in
[NOTICE](NOTICE). Third-party licenses: [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES).
