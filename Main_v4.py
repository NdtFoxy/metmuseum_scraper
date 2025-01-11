import os
import requests
import random
from bs4 import BeautifulSoup as bs
import json
import signal
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging
from tqdm import tqdm
import argparse
import yaml
from pythonjsonlogger import jsonlogger

# Suppress warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global variables from the configuration file
config = {}
url_base = ""
headers = {}
output_folder = ""
json_folder = ""
image_folder = ""  # New variable for the image folder
proxy_list = []
total_pages = 0

stop_execution = False
logger = None  # Initialize logger globally

def load_config(config_path="config.yaml"):
    """Loads the configuration from a YAML file."""
    global config, url_base, headers, output_folder, json_folder, image_folder, proxy_list, total_pages
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    url_base = config["url_base"]
    headers = config["headers"]
    output_folder = config["output_folder"]
    json_folder = os.path.join(output_folder, "json")
    image_folder = os.path.join(output_folder, "image")  # Define the image folder path
    proxy_list = config["proxy_list"]
    total_pages = config["total_pages"]

    os.makedirs(json_folder, exist_ok=True)
    os.makedirs(image_folder, exist_ok=True)  # Create the image folder
    create_gitignore(image_folder)

def handle_interrupt(signal_received, frame):
    """Handles Ctrl+C or other interruptions."""
    global stop_execution
    global logger
    log_event("info", "interrupt", {"message": "Script interrupted. Saving progress..."})
    stop_execution = True

signal.signal(signal.SIGINT, handle_interrupt)

def get_session(proxy):
    """Creates a requests session with the specified proxy."""
    session = requests.Session()
    session.proxies = {
        "http": f"socks5://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}",
        "https": f"socks5://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
    }
    return session

def setup_logging():
    """Configures JSON logging with detailed fields."""
    global logger
    log_dir = config.get("log_dir", "Logs")
    log_level = getattr(logging, config.get("log_level", "DEBUG").upper())

    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, f"log_{time.strftime('%Y%m%d_%H%M%S')}.json")

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    log_handler = logging.FileHandler(log_filename)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    log_event("info", "init", {"message": "Logging initialized", "log_file": log_filename})
    return logger

def log_event(status, action, details=None):
    """Helper to log events with structured data."""
    log_data = {
        "status": status,
        "action": action,
        "details": details or {}
    }
    logger.info(json.dumps(log_data))

def analyze_logs(log_dir):
    """Analyzes logs to determine already processed pages and artifacts."""
    processed_pages = set()
    failed_pages = set()
    with os.scandir(log_dir) as entries:
        for entry in entries:
            if entry.is_file() and entry.name.endswith(".json"):
                with open(entry.path, "r", encoding="utf-8") as log_file:
                    for line in log_file:
                        try:
                            log_entry = json.loads(line.strip())
                            if log_entry.get("status") == "success" and log_entry.get("action") == "process_page":
                                processed_pages.add(log_entry["details"]["page_number"])
                            elif log_entry.get("status") == "failure" and log_entry.get("action") == "fetch_page":
                                failed_pages.add(log_entry["details"]["page_number"])
                        except json.JSONDecodeError:
                            continue
    return processed_pages, failed_pages

def create_gitignore(folder_path):
    """Creates a .gitignore file in the specified folder to ignore all files except the .gitignore itself."""
    gitignore_path = os.path.join(folder_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write("# Ignore everything in this directory\n")
            f.write("*\n")
            f.write("# Except this file\n")
            f.write("!.gitignore\n")

def process_page(proxy, count_page, pbar, all_artifacts_data):
    """Processes a single page of artifacts, fetches data, and saves it to JSON and images."""
    global logger
    log_event("info", "start_page", {"message": f"Starting processing page {count_page}", "proxy": f"{proxy['ip']}:{proxy['port']}", "country": proxy['country_code'], "page_number": count_page})

    min_delay = config.get("min_request_delay", 1)
    max_delay = config.get("max_request_delay", 3)
    time.sleep(random.uniform(min_delay, max_delay))

    url = url_base if count_page == 1 else f"{url_base}&offset={(count_page - 1) * 40}"

    session = get_session(proxy)

    max_retries = config.get("max_retries", 3)
    retry_delay = config.get("retry_delay", 5)

    for attempt in range(max_retries):
        try:
            req = session.get(url, headers=headers, verify=False, timeout=15)
            req.raise_for_status()
            src = req.text
            log_event("success", "fetch_page", {"page_number": count_page, "url": url, "attempt": attempt + 1})
            break
        except requests.RequestException as e:
            log_event("retry", "fetch_page", {"page_number": count_page, "url": url, "error": str(e), "attempt": attempt + 1})
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                log_event("failure", "fetch_page", {"page_number": count_page, "url": url, "error": str(e), "attempts": max_retries})
                pbar.update(1)
                return

    soup = bs(src, "lxml")
    all_arts_hrefs = soup.find_all(class_="redundant-link_redundantlink__b5TFR")
    array = ["https://www.metmuseum.org" + item.get("href") for item in all_arts_hrefs]

    artifact_counter = 1  # Нумерация артефактов на странице
    for href in array:
        if stop_execution:
            log_event("info", "interrupt", {"message": "Exiting gracefully."})
            break

        for attempt in range(max_retries):
            try:
                req = session.get(href, headers=headers, verify=False, timeout=15)
                req.raise_for_status()
                page_src = req.text
                log_event("success", "fetch_artifact", {"page_number": count_page, "artifact_url": href, "attempt": attempt + 1})
                break
            except requests.RequestException as e:
                log_event("retry", "fetch_artifact", {"page_number": count_page, "artifact_url": href, "error": str(e), "attempt": attempt + 1})
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    log_event("failure", "fetch_artifact", {"page_number": count_page, "artifact_url": href, "error": str(e), "attempts": max_retries})
                    break
        else:
            continue

        soup2 = bs(page_src, "lxml")

        info_from_art = soup2.find_all(class_="artwork-tombstone--item")
        art_details = {}

        for item in info_from_art:
            key_element = item.find("span", class_="artwork-tombstone--label")
            value_element = item.find("span", class_="artwork-tombstone--value")

            if key_element and value_element:
                key = key_element.get_text(strip=True)
                value = value_element.get_text(strip=True)
                art_details[key] = value

        sections = {
            "Catalogue Entry": "catalogue-entry",
            "Technical Notes": "technical-notes",
            "Signatures, Inscriptions, and Markings": "signatures-inscriptions-and-markings",
            "Provenance": "provenance",
            "Exhibition History": "exhibition-history",
            "References": "references",
            "Frame": "frame",
            "Notes": "notes",
            "Loan Restrictions": "loan-restrictions"
        }

        for section_name, section_id in sections.items():
            section_data = soup2.find(id=section_id)
            if section_data:
                art_details[section_name] = section_data.get_text(strip=True)

        intro_desc = soup2.find(class_="artwork__intro__desc js-artwork__intro__desc")
        if intro_desc:
            art_details["Intro Description"] = intro_desc.get_text(strip=True)

        image_links = []
        main_image = soup2.find("img", class_="artwork__image")
        if main_image:
            image_links.append(main_image.get("src"))

        if image_links:
            art_details["Image Links"] = image_links

            for img_url in image_links:
                image_name = f"{count_page}_{artifact_counter}.jpg"
                image_path = os.path.join(image_folder, image_name)

                for attempt in range(max_retries):
                    try:
                        img_data = session.get(img_url, headers=headers, verify=False, timeout=15).content
                        with open(image_path, "wb") as img_file:
                            img_file.write(img_data)
                        log_event("success", "save_image", {"page_number": count_page, "artifact_url": href, "image_url": img_url, "filename": image_name, "attempt": attempt + 1})
                        break
                    except Exception as e:
                        log_event("retry", "save_image", {"page_number": count_page, "artifact_url": href, "image_url": img_url, "error": str(e), "attempt": attempt + 1})
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                        else:
                            log_event("failure", "save_image", {"page_number": count_page, "artifact_url": href, "image_url": img_url, "error": str(e), "attempts": max_retries})
                            break

        art_details["Source URL"] = href
        all_artifacts_data.append(art_details)

        artifact_counter += 1  # Увеличиваем номер артефакта на странице

    log_event("success", "process_page", {"page_number": count_page, "artifacts_processed": artifact_counter -1 })
    pbar.update(1)

def main():
    """Main function to start the scraping process."""
    global logger
    logger = setup_logging()
    all_artifacts_data = []

    processed_pages, failed_pages = analyze_logs(config["log_dir"])
    remaining_pages = [p for p in range(1, total_pages + 1) if p not in processed_pages]
    
    if not remaining_pages:
        log_event("info", "completed", {"message": "All pages have already been processed."})
        print("All pages have already been processed.")
        return

    with ThreadPoolExecutor(max_workers=len(proxy_list)) as executor:
        futures = []
        page_counter = remaining_pages[0] 
        with tqdm(initial=len(processed_pages), total=total_pages, desc="Processing Pages") as pbar:
            while page_counter <= total_pages:
                for i in range(len(proxy_list)):
                    if page_counter <= total_pages and page_counter not in processed_pages:
                        future = executor.submit(process_page, proxy_list[i], page_counter, pbar, all_artifacts_data)
                        futures.append(future)
                        page_counter += 1
                    elif page_counter in processed_pages:
                        page_counter += 1

            for future in as_completed(futures):
                future.result()

    # Save all artifact data to a single JSON file
    with open(os.path.join(json_folder, "all_artifacts_data.json"), "w", encoding="utf-8") as file:
        json.dump(all_artifacts_data, file, indent=4, ensure_ascii=False)
    log_event("info", "save_data", {"message": "All artifacts data saved to all_artifacts_data.json"})

def help_command():
    """
    Prints a concise help message with essential information.
    """
    help_text = """
## **Met Museum Artifact Scraper**

This script retrieves artifact information from the Metropolitan Museum of Art website.

### **Quick Start:**

**1. Docker Compose (Recommended):**

*   **Build:** `docker-compose build`
*   **Run (detached):** `docker-compose up -d`
*   **Execute script:**
    *   `run`: `docker exec -it metmuseum_scraper python Main_v4.py run`
    *   `help`: `docker exec -it metmuseum_scraper python Main_v4.py help`

**2. Run Script Directly (Without Docker):**

*   **Run scraper:** `python Main_v4.py run`
*   **Help:** `python Main_v4.py help`

### **Commands:**

| Command | Description                                                                 |
| :------ | :-------------------------------------------------------------------------- |
| `run`   | Starts the scraping process.                                                |
| `help`  | Shows this help message with command and function details, plus Docker use. |

### **Key Functions:**

| Function                                 | Description                                                                                      |
| :--------------------------------------- | :----------------------------------------------------------------------------------------------- |
| `process_page(proxy, ...)`               | Fetches and processes a single page of artifacts.                                                |
| `get_session(proxy)`                     | Creates a requests session with a specified proxy.                                               |
| `setup_logging()`                        | Sets up logging to record events.                                                                |
| `handle_interrupt(...)`                  | Gracefully handles Ctrl+C to save progress.                                                      |
| `main()`                                 | The main function that orchestrates the scraping.                                                |
| `load_config(...)`                       | Loads settings from `config.yaml`.                                                               |
| `create_gitignore(...)`                  | Creates a `.gitignore` in image folders to exclude them from Git.                                |
| `log_event(...)`                         | Logs events (success, failure, etc.) with details.                                               |
| `analyze_logs(...)`                      | Analyzes logs to track processed and failed pages, enabling resume functionality.                |

### **Important Notes:**

*   Uses multiple proxies (configure in `config.yaml`).
*   Logs are saved in the `Logs` directory (or as set in `config.yaml`).
*   Output (JSON and images) goes to `Save_Data/Arts_Data` (or as set in `config.yaml`).
*   Handles Ctrl+C to save progress before exiting.
*   Configuration is from `config.yaml`.
*   Image folders have `.gitignore` to prevent accidental Git commits.
*   Make sure you have Docker and Docker Compose installed if you want to use the Docker method.
*   Each folder with images will have a .gitignore file to prevent accidental commits of images to a Git repository.
*   Analyzes log files to determine which pages have been processed or failed, allowing the script to resume from where it left off.
*   Creates a .gitignore file in the specified folder to ignore all files except the .gitignore itself, useful for excluding downloaded images from Git.
*   Loads the configuration settings from a YAML file (default: `config.yaml`), setting up parameters like URLs, headers, proxies, etc.
*   Entry point of the application. Manages concurrent processing of multiple pages using ThreadPoolExecutor to speed up the data fetching process.
*   Handles interruptions (e.g., Ctrl+C or SIGINT) gracefully, ensuring that any data being processed is saved before the script exits.
*   Configures and returns a logger for logging application messages, including errors, warnings, and informational messages.
*   Creates and returns a requests.Session object configured with the provided proxy settings for making HTTP requests.
*   Fetches and processes a specific page of artifacts, extracting details and downloading related images.
*   Displays this help message with available commands, their descriptions, and Docker instructions.
*   Executes the main scraping process.
    """
    print(help_text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to process art pages with proxy support.")
    parser.add_argument(
        "command",
        choices=["run", "help"],
        help="Specify 'run' to execute the script or 'help' to display available commands and their descriptions."
    )

    args = parser.parse_args()

    load_config()

    if args.command == "help":
        help_command()
    elif args.command == "run":
        main()