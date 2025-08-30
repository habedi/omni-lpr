import argparse

import httpx


def main():
    """Sends a request to the list_models tool and prints the result."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:8000/api/v1/tools/list_models/invoke",
        help="The URL for the endpoint.",
    )
    args = parser.parse_args()

    print(f"Sending request to {args.url}")

    try:
        # Send the POST request
        response = httpx.post(args.url, timeout=30, json={})
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
