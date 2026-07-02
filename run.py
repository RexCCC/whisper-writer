import glob
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def set_cuda_paths():
    """Set up CUDA paths for GPU support."""
    try:
        cuda_base_path = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
        if not os.path.exists(cuda_base_path):
            print("NVIDIA CUDA Toolkit folder not found")
            return

        cuda_versions = glob.glob(os.path.join(cuda_base_path, "v12.*"))
        cuda_versions.sort(
            key=lambda x: [int(n) for n in x.split("v")[1].split(".")],
            reverse=True,
        )
        if not cuda_versions:
            print("No CUDA 12.x installation found in system")
            return

        system_cuda_path = cuda_versions[0]
        cuda_version = os.path.basename(system_cuda_path)[1:]
        print(f"Found system CUDA version: {cuda_version}")

        paths_to_add = [
            os.path.join(system_cuda_path, "bin"),
            os.path.join(system_cuda_path, "libnvvp"),
        ]
        cudnn_path = os.path.join(system_cuda_path, "cudnn")
        if os.path.exists(cudnn_path):
            paths_to_add.append(os.path.join(cudnn_path, "bin"))

        print(f"Using system CUDA from: {system_cuda_path}")
        env_vars = ["CUDA_PATH", f"CUDA_PATH_V{cuda_version.replace('.', '_')}", "PATH"]
        for env_var in env_vars:
            current_value = os.environ.get(env_var, "")
            new_value = os.pathsep.join(
                paths_to_add + [current_value] if current_value else paths_to_add
            )
            os.environ[env_var] = new_value

        print("CUDA paths set up successfully")
    except Exception as e:
        print(f"Error setting up CUDA paths: {e}")
        print("Falling back to CPU mode")


def main():
    app_root = Path(__file__).resolve().parent
    os.chdir(app_root)
    src_dir = app_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    set_cuda_paths()
    load_dotenv()
    print("Starting WhisperWriter...")

    from utils import ConfigManager
    from transcription import create_local_model

    ConfigManager.initialize()

    preloaded_local_model = None
    if not ConfigManager.get_config_section("model_options").get("use_api"):
        model_name = ConfigManager.get_config_value("model_options", "local", "model")
        print(f"Loading speech model ({model_name})... tray icon appears when ready.")
        try:
            preloaded_local_model = create_local_model()
        except Exception as exc:
            print(f"Model load failed: {exc}")
            preloaded_local_model = None

    from main import start_app

    start_app(preloaded_local_model)


if __name__ == "__main__":
    main()
