import requests
import json
import time
import argparse
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the default API endpoint
DEFAULT_API_URL = "http://localhost:8000/tickets/"
DEFAULT_DELAY_SECONDS = 10
DEFAULT_FILE_PATH = "synthetic_tickets.jsonl"

def send_ticket(api_url: str, subject: str, body: str) -> bool:
    """
    Sends a single ticket to the specified API endpoint.

    Args:
        api_url: The URL of the API endpoint.
        subject: The subject of the ticket.
        body: The body content of the ticket.

    Returns:
        True if the request was successful (2xx status code), False otherwise.
    """
    payload = {
        "subject": subject,
        "body": body
    }
    try:
        response = requests.post(api_url, json=payload, timeout=30) # Added timeout
        if 200 <= response.status_code < 300:
            logging.info(f"Successfully sent ticket: '{subject[:50]}...' - Status: {response.status_code} - Response: {response.json()}")
            return True
        else:
            logging.error(f"Failed to send ticket: '{subject[:50]}...' - Status: {response.status_code} - Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending ticket: '{subject[:50]}...' - Exception: {e}")
        return False

def process_tickets_file(file_path: str, api_url: str, delay_seconds: int):
    """
    Reads tickets from a JSON Lines file and sends them one by one.

    Args:
        file_path: Path to the .jsonl file containing ticket data.
        api_url: The URL of the API endpoint to send tickets to.
        delay_seconds: The delay in seconds between sending each ticket.
    """
    logging.info(f"Starting to process tickets from: {file_path}")
    logging.info(f"Sending to API endpoint: {api_url}")
    logging.info(f"Delay between tickets: {delay_seconds} seconds")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                try:
                    ticket_data = json.loads(line.strip())
                except json.JSONDecodeError:
                    logging.warning(f"Skipping malformed JSON line {i+1}: {line.strip()}")
                    continue

                subject = ticket_data.get("subject")
                body = ticket_data.get("body")

                if subject is None or body is None:
                    logging.warning(f"Skipping line {i+1} due to missing 'subject' or 'body': {ticket_data}")
                    continue

                logging.info(f"Processing ticket {i+1}/{sum(1 for _ in open(file_path)) if i == 0 else '?'}: Subject - '{subject[:50]}...'") # Show progress on first ticket
                
                if send_ticket(api_url, subject, body):
                    logging.info(f"Waiting for {delay_seconds} seconds before sending the next ticket...")
                else:
                    logging.warning(f"Will still wait for {delay_seconds} seconds despite previous error.")
                
                time.sleep(delay_seconds)
            
            logging.info("Finished processing all tickets in the file.")

    except FileNotFoundError:
        logging.error(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send synthetic tickets to an API endpoint.")
    parser.add_argument(
        "--file", 
        type=str, 
        default=DEFAULT_FILE_PATH,
        help=f"Path to the JSON Lines file containing tickets (default: {DEFAULT_FILE_PATH})"
    )
    parser.add_argument(
        "--url", 
        type=str, 
        default=DEFAULT_API_URL,
        help=f"API endpoint URL to post tickets to (default: {DEFAULT_API_URL})"
    )
    parser.add_argument(
        "--delay", 
        type=int, 
        default=DEFAULT_DELAY_SECONDS,
        help=f"Delay in seconds between sending each ticket (default: {DEFAULT_DELAY_SECONDS})"
    )

    args = parser.parse_args()

    process_tickets_file(args.file, args.url, args.delay)
# This script will read tickets from a JSON Lines file and send them to the specified API endpoint.