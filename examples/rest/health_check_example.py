import argparse

import httpx


def main():
    """Performs a health check against the server."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:8000/api/health",
        help="The URL for the health check endpoint.",
    )
    args = parser.parse_args()

    print(f"Sending health check request to {args.url}")

    try:
        # Send the GET request
        response = httpx.get(args.url, timeout=10)
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
