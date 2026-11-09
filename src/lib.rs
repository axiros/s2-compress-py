//! s2compress: S2 block compression for Python, over the minlz crate. The block format is the
//! one of Go's `github.com/klauspost/compress/s2` `Encode`/`Decode`: a frame written by either
//! side reads on the other. No dictionaries. The GIL is released while bytes are worked on.

use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

create_exception!(s2compress, S2Error, PyValueError, "Not an S2 block, or larger than allowed");

/// Default upper bound of [`decompress`]: a payload larger than this is refused before any
/// memory is allocated for it
const DEFAULT_MAX: usize = 64 << 20;

/// The largest input compress takes. minlz 1.2.3 writes a broken block above about 16.06 MiB
/// (16 842 795 bytes and more; Go's decoder rejects it too), so compress stops at 16 MiB. Its
/// decoder reads larger blocks written by Go. NATS payloads are 1 MiB by default
const MAX_COMPRESS: usize = 16 << 20;

/// compress(data) -> bytes: the S2 block of data; data larger than 16 MiB is refused with
/// S2Error (send it uncompressed)
#[pyfunction]
fn compress<'py>(py: Python<'py>, data: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
    if data.len() > MAX_COMPRESS {
        return Err(S2Error::new_err(format!(
            "{} bytes: compress takes at most {MAX_COMPRESS}",
            data.len()
        )));
    }
    let out = py.allow_threads(|| minlz::encode(data));
    Ok(PyBytes::new(py, &out))
}

/// decoded_len(data) -> int: the size data decompresses to, from the block header
#[pyfunction]
fn decoded_len(data: &[u8]) -> PyResult<usize> {
    minlz::decode_len(data)
        .map(|(n, _)| n)
        .map_err(|e| S2Error::new_err(format!("not an S2 block: {e}")))
}

/// decompress(data, max_size=64 MiB) -> bytes: the bytes of an S2 block. A block that says it
/// is larger than max_size is refused before it is decoded
#[pyfunction]
#[pyo3(signature = (data, max_size = DEFAULT_MAX))]
fn decompress<'py>(py: Python<'py>, data: &[u8], max_size: usize) -> PyResult<Bound<'py, PyBytes>> {
    let n = decoded_len(data)?;
    if n > max_size {
        return Err(S2Error::new_err(format!(
            "the block decompresses to {n} bytes, more than max_size {max_size}"
        )));
    }
    let out = py
        .allow_threads(|| minlz::decode(data))
        .map_err(|e| S2Error::new_err(format!("not an S2 block: {e}")))?;
    Ok(PyBytes::new(py, &out))
}

#[pymodule]
fn s2compress(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compress, m)?)?;
    m.add_function(wrap_pyfunction!(decompress, m)?)?;
    m.add_function(wrap_pyfunction!(decoded_len, m)?)?;
    m.add("S2Error", m.py().get_type::<S2Error>())?;
    m.add("DEFAULT_MAX", DEFAULT_MAX)?;
    m.add("MAX_COMPRESS", MAX_COMPRESS)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
