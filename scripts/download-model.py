"""Download a faster-whisper model into the HuggingFace cache."""
import argparse
import glob
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

cuda_base = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
if os.path.exists(cuda_base):
    versions = sorted(glob.glob(os.path.join(cuda_base, "v12.*")), reverse=True)
    if versions:
        cuda_path = versions[0]
        ver = os.path.basename(cuda_path)[1:]
        paths = [os.path.join(cuda_path, "bin"), os.path.join(cuda_path, "libnvvp")]
        for key in ("CUDA_PATH", f"CUDA_PATH_V{ver.replace('.', '_')}", "PATH"):
            current = os.environ.get(key, "")
            os.environ[key] = os.pathsep.join(paths + ([current] if current else []))

from faster_whisper import WhisperModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", nargs="?", default="distil-medium.en")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute-type", default="float16")
    args = parser.parse_args()

    print(f"Downloading/loading {args.model} ({args.device}, {args.compute_type})...")
    print("This can take several minutes on first download.")
    WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    print(f"Ready: {args.model}")


if __name__ == "__main__":
    main()
