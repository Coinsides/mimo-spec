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

Or use the one-click scripts:
- `install.ps1`
- `install.bat`

Compatibility wrappers:
- `mimo-pack.bat` / `mimo-validate.bat` / `mimo-extract.bat`
- `mimo-pack.ps1` / `mimo-validate.ps1` / `mimo-extract.ps1`

> Note: `ffmpeg` is required for audio extraction. Install it via your OS package manager.

## Dependencies
- **Minimal**: PyYAML
- **Optional (OCR / STT)**: EasyOCR, faster-whisper, ffmpeg

## Quickstart (3 lines)
```bash
pip install -r requirements.txt
mimo-pack
mimo-extract
```

## Usage
```bash
mimo-pack
mimo-validate
mimo-extract
```

## Output Paths
- Generated `.mimo`: `C:\Mimo\mimo_data\Test\.mimo_samples\mimo`
- Assets index: `C:\Mimo\mimo_data\Test\.mimo_samples\assets\asset_index.jsonl`
- Reconstructed output: `C:\Mimo\mimo_data\Test\.mimo_samples\reconstructed`

## Examples
See `examples/` for minimal English samples and reconstructed outputs.

## Acknowledgements
We rely on the following open-source projects and tools:
- EasyOCR
- faster-whisper
- ffmpeg
- PyYAML

## License
MIT
