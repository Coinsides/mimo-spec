# MIMO Spec

Spec + tools for MU (`.mimo`) format.

## What is MU (.mimo)?
MU is the minimal memory unit used for storage, retrieval, and reconstruction. A `.mimo` file is a YAML document with:
- `summary`
- `pointer`
- `meta`
- `snapshot_gz_b64`

## Tools
- **mimo-pack**: generate `.mimo` from raw inputs
- **mimo-validate**: validate `.mimo` structure
- **mimo-extract**: reconstruct snapshots and assets

## Install
```bash
pip install -r requirements.txt
```

> Note: `ffmpeg` is required for audio extraction. Install it via your OS package manager.

## Usage
```bash
python tools/mimo-pack.py
python tools/mimo-validate.py
python tools/mimo-extract.py
```

## Output Paths
- Generated `.mimo`: `C:\Mimo\mimo_data\Test\.mimo_samples\mimo`
- Assets index: `C:\Mimo\mimo_data\Test\.mimo_samples\assets\asset_index.jsonl`
- Reconstructed output: `C:\Mimo\mimo_data\Test\.mimo_samples\reconstructed`

## Examples
See `examples/` for minimal English samples.

## Acknowledgements
We rely on the following open-source projects and tools:
- EasyOCR
- faster-whisper
- ffmpeg
- PyYAML

## License
MIT
