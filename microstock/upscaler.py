"""Upscaler module wrapping Real-ESRGAN NCNN Vulkan CLI."""
import os
import subprocess
from typing import Optional

def get_upscaler_binary_path() -> Optional[str]:
    """Return the absolute path to the upscaler binary if it exists."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # For macos, the binary inside the extracted zip is 'realesrgan-ncnn-vulkan'
    bin_path = os.path.join(base_dir, "upscayl_bin", "realesrgan-ncnn-vulkan")
    if os.path.exists(bin_path):
        # ensure it's executable
        os.chmod(bin_path, 0o755)
        return bin_path
    return None

def is_upscale_needed(width: int, height: int) -> bool:
    """Return True if image resolution is below microstock standard (4.2 Megapixels)."""
    from . import config
    return (width * height) < config.TARGET_MIN_PIXELS


def calculate_required_scale(width: int, height: int, user_scale: int = 4) -> int:
    """Calculate required scale. Always returns 4 for x4 AI super-resolution models."""
    return 4


def run_upscale(
    input_path: str,
    output_path: str,
    scale: int = 4,
    model: str = "realesrgan-x4plus",
    tile_size: int = 400,
) -> bool:
    """Run the upscaler on the input file and save to output_path.
    
    Returns True if successful, False otherwise.
    """
    bin_path = get_upscaler_binary_path()
    if not bin_path:
        raise FileNotFoundError("Mesin upscaler NCNN CLI tidak ditemukan di folder upscayl_bin.")

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
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=os.path.join(base_dir, "upscayl_bin")
        )
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except subprocess.CalledProcessError as e:
        print(f"Upscaler error: {e.stderr}")
        return False
    except Exception as e:
        print(f"Failed to execute upscaler: {e}")
        return False
