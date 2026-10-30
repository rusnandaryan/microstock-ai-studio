"""Upscaler module wrapping Real-ESRGAN NCNN Vulkan CLI."""
import os
import subprocess
from typing import Optional, Tuple

def get_upscaler_binary_path() -> Optional[str]:
    """Return the absolute path to the upscaler binary if it exists."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bin_path = os.path.join(base_dir, "upscayl_bin", "realesrgan-ncnn-vulkan")
    if os.path.exists(bin_path):
        if not os.access(bin_path, os.X_OK):
            try:
                os.chmod(bin_path, 0o755)
            except OSError:
                pass
        return bin_path
    return None

def is_upscale_needed(width: int, height: int) -> bool:
    """Return True if image resolution is below microstock standard (4.2 Megapixels)."""
    from . import config
    return (width * height) < config.TARGET_MIN_PIXELS


def run_upscale(
    input_path: str,
    output_path: str,
    scale: int = 4,
    model: str = "realesrgan-x4plus",
    tile_size: int = 400,
) -> Tuple[bool, Optional[str]]:
    """Run the upscaler on the input file and save to output_path.
    
    Returns (success: bool, error_message: Optional[str]).
    """
    bin_path = get_upscaler_binary_path()
    if not bin_path:
        return False, "Mesin upscaler NCNN CLI tidak ditemukan di folder upscayl_bin."

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, "upscayl_bin", "models")
    abs_input = os.path.abspath(input_path)
    abs_output = os.path.abspath(output_path)

    # realesrgan-x4plus is strictly an x4 model. Forcing scale 2 or 3 on a 4x model
    # causes NCNN to miscalculate tile strides, scrambling the image into overlapping jigsaw squares.
    actual_scale = 4 if "x4" in model else scale

    cmd = [
        bin_path,
        "-i", abs_input,
        "-o", abs_output,
        "-m", models_dir,
        "-s", str(actual_scale),
        "-t", str(tile_size),
        "-n", model,
    ]
    
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=os.path.join(base_dir, "upscayl_bin")
        )
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, None
        return False, "Berkas output kosong atau gagal dibuat oleh NCNN."
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else str(e)
        return False, err_msg
    except Exception as e:
        return False, str(e)
