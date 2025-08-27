import argparse
import base64
import os


def get_args(default_url: str):
    """Parses and returns command-line arguments for the examples."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image-path",
        type=str,
        default="tests/testdata/plates/Eecs00c.png",
        help="The absolute or relative path to the image.",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=default_url,
        help="The URL for the endpoint.",
    )
    return parser.parse_args()


def get_image_base64(image_path: str) -> str | None:
    """Reads an image file and returns its base64-encoded content."""
    abs_image_path = os.path.abspath(image_path)
    try:
        with open(abs_image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"Error: Image file not found at {abs_image_path}")
        return None
