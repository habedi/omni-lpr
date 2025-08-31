import httpx

from shared import get_args


def main():
    """Sends an image to the REST API as a file upload for detection and recognition, and prints the result."""
    args = get_args(
        default_url="http://127.0.0.1:8000/api/v1/tools/detect_and_recognize_plate/invoke"
    )

    print(f"Sending request to {args.url} with image file: {args.image_path}")

    try:
        with open(args.image_path, "rb") as f:
            # The 'files' parameter is used to send multipart/form-data.
            # We build a dictionary where each value is a tuple. For form fields,
            # the tuple is (None, value), and for files, it's (filename, file-like-object, content-type).
            files = {
                "image": (args.image_path, f, "image/png"),
                "detector_model": (None, "yolo-v9-t-384-license-plate-end2end"),
                "ocr_model": (None, "cct-s-v1-global-model"),
            }

            # Send the POST request
            response = httpx.post(args.url, files=files, timeout=30)
            response.raise_for_status()

            # Print the result
            print("Response from server:")
            print(response.json())

    except FileNotFoundError:
        print(f"Error: Image file not found at {args.image_path}")
    except httpx.RequestError as e:
        print(f"An error occurred while requesting {e.request.url!r}.")
        print(e)
    except httpx.HTTPStatusError as e:
        print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
        print(f"Response body: {e.response.text}")


if __name__ == "__main__":
    main()
