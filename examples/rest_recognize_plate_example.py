import httpx

from shared import get_args, get_image_base64


def main():
    """Sends a license plate image to the REST API and prints the result."""
    args = get_args(default_url="http://127.0.0.1:8000/api/v1/tools/recognize_plate/invoke")

    # Read the image file and encode it in base64
    image_base64 = get_image_base64(args.image_path)
    if not image_base64:
        return

    # The data to send in the POST request
    data = {"image_base64": image_base64}

    print(f"Sending request to {args.url} with image: {args.image_path}")

    try:
        # Send the POST request
        response = httpx.post(args.url, json=data, timeout=30)
        response.raise_for_status()

        # Print the result
        print("Response from server:")
        print(response.json())

    except httpx.RequestError as e:
        print(f"An error occurred while requesting {e.request.url!r}.")
        print(e)
    except httpx.HTTPStatusError as e:
        print(f"Error response {e.response.status_code} while requesting {e.request.url!r}.")
        print(f"Response body: {e.response.text}")


if __name__ == "__main__":
    main()
