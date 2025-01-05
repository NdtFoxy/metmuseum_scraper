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
proxy_list = []
total_pages = 0

stop_execution = False
logger = None  # Initialize logger globally

def load_config(config_path="config.yaml"):
    """Loads the configuration from a YAML file."""
    global config, url_base, headers, output_folder, json_folder, proxy_list, total_pages
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    url_base = config["url_base"]
    headers = config["headers"]
    output_folder = config["output_folder"]
    json_folder = os.path.join(output_folder, "json")
    proxy_list = config["proxy_list"]
    total_pages = config["total_pages"]

    os.makedirs(json_folder, exist_ok=True)

def handle_interrupt(signal_received, frame):
    """Handles Ctrl+C or other interruptions."""
    global stop_execution
    global logger
    logger.info("Script interrupted. Saving progress...")
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
    """Configures logging to use JSON format."""
    global logger
    log_dir = config.get("log_dir", "Logs")
    log_level = getattr(logging, config.get("log_level", "DEBUG").upper())
    
    os.makedirs(log_dir, exist_ok=True)
    session_num = 1
    while True:
        log_filename = os.path.join(log_dir, f"Logs_Session_{session_num}.json")  # Use .json extension
        if not os.path.exists(log_filename):
            break
        session_num += 1

    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    log_handler = logging.FileHandler(log_filename)
    formatter = jsonlogger.JsonFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    
    return logger

def create_gitignore(folder_path):
    """Creates a .gitignore file in the specified folder to ignore all files except the .gitignore itself."""
    gitignore_path = os.path.join(folder_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write("# Ignore everything in this directory\n")
            f.write("*\n")
            f.write("# Except this file\n")
            f.write("!.gitignore\n")

def process_page(proxy, count_page, pbar):
    """Processes a single page of artifacts, fetches data, and saves it to JSON and images."""
    global logger
    logger.info(json.dumps({"message": f"Starting processing page {count_page}", "proxy": f"{proxy['ip']}:{proxy['port']}", "country": proxy['country_code']}))

    min_delay = config.get("min_request_delay", 1)
    max_delay = config.get("max_request_delay", 3)
    time.sleep(random.uniform(min_delay, max_delay))

    url = url_base if count_page == 1 else f"{url_base}&offset={(count_page - 1) * 40}"
    page_json_path = os.path.join(json_folder, f"Page_{count_page}_data.json")

    if os.path.exists(page_json_path):
        logger.info(json.dumps({"message": f"Data for page {count_page} already exists. Skipping...", "page": count_page}))
        pbar.update(1)
        return

    session = get_session(proxy)

    max_retries = config.get("max_retries", 3)
    retry_delay = config.get("retry_delay", 5)

    for attempt in range(max_retries):
        try:
            req = session.get(url, headers=headers, verify=False, timeout=15)
            req.raise_for_status()
            src = req.text
            logger.info(json.dumps({"message": f"Successfully fetched page {count_page}", "page": count_page, "attempt": attempt + 1}))
            break
        except requests.RequestException as e:
            logger.warning(json.dumps({"message": f"Attempt {attempt + 1} failed for page {count_page}", "page": count_page, "error": str(e)}))
            if attempt < max_retries - 1:
                logger.info(json.dumps({"message": f"Retrying in {retry_delay} seconds...", "page": count_page, "attempt": attempt + 1, "delay": retry_delay}))
                time.sleep(retry_delay)
            else:
                logger.error(json.dumps({"message": f"Failed to fetch page {count_page} after {max_retries} attempts", "page": count_page, "attempts": max_retries}))
                pbar.update(1)
                return

    soup = bs(src, "lxml")
    all_arts_hrefs = soup.find_all(class_="redundant-link_redundantlink__b5TFR")
    array = ["https://www.metmuseum.org" + item.get("href") for item in all_arts_hrefs]

    artifacts_data = []
    page_images_folder = os.path.join(output_folder, f"Page_{count_page}")
    os.makedirs(page_images_folder, exist_ok=True)
    create_gitignore(page_images_folder)

    for href in array:
        if stop_execution:
            logger.info("Exiting gracefully.")
            break

        for attempt in range(max_retries):
            try:
                req = session.get(href, headers=headers, verify=False, timeout=15)
                req.raise_for_status()
                page_src = req.text
                logger.info(json.dumps({"message": f"Successfully fetched artifact details from {href}", "page": count_page, "artifact": href, "attempt": attempt + 1}))
                break
            except requests.RequestException as e:
                logger.warning(json.dumps({"message": f"Attempt {attempt + 1} failed to fetch artifact details from {href}", "page": count_page, "artifact": href, "error": str(e)}))
                if attempt < max_retries - 1:
                    logger.info(json.dumps({"message": f"Retrying in {retry_delay} seconds...", "page": count_page, "artifact": href, "attempt": attempt + 1, "delay": retry_delay}))
                    time.sleep(retry_delay)
                else:
                    logger.error(json.dumps({"message": f"Failed to fetch artifact details from {href} after {max_retries} attempts", "page": count_page, "artifact": href, "attempts": max_retries}))
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

            for idx, img_url in enumerate(image_links):
                image_name = f"{href.split('/')[-1]}_{idx}.jpg"
                image_path = os.path.join(page_images_folder, image_name)

                for attempt in range(max_retries):
                    try:
                        img_data = session.get(img_url, headers=headers, verify=False, timeout=15).content
                        with open(image_path, "wb") as img_file:
                            img_file.write(img_data)
                        logger.info(json.dumps({"message": f"Successfully saved image {img_url}", "page": count_page, "artifact": href, "image": img_url, "attempt": attempt + 1}))
                        break
                    except Exception as e:
                        logger.warning(json.dumps({"message": f"Attempt {attempt + 1} failed to save image {img_url}", "page": count_page, "artifact": href, "image": img_url, "error": str(e)}))
                        if attempt < max_retries - 1:
                            logger.info(json.dumps({"message": f"Retrying in {retry_delay} seconds...", "page": count_page, "artifact": href, "image": img_url, "attempt": attempt + 1, "delay": retry_delay}))
                            time.sleep(retry_delay)
                        else:
                            logger.error(json.dumps({"message": f"Failed to save image {img_url} after {max_retries} attempts", "page": count_page, "artifact": href, "image": img_url, "attempts": max_retries}))
                            break

        artifacts_data.append(art_details)

    if not stop_execution:
        with open(page_json_path, "w", encoding="utf-8") as file:
            json.dump(artifacts_data, file, indent=4, ensure_ascii=False)

    logger.info(json.dumps({"message": f"Page {count_page} is ready", "page": count_page}))
    pbar.update(1)

def main():
    """Main function to start the scraping process."""
    global logger
    logger = setup_logging()
    
    with ThreadPoolExecutor(max_workers=len(proxy_list)) as executor:
        futures = []
        page_counter = 1
        with tqdm(total=total_pages, desc="Processing Pages") as pbar:
            while page_counter <= total_pages:
                for i in range(len(proxy_list)):
                    if page_counter <= total_pages:
                        future = executor.submit(process_page, proxy_list[i], page_counter, pbar)
                        futures.append(future)
                        page_counter += 1

            for future in as_completed(futures):
                future.result()

def help_command():
    """
    Prints out a list of available commands, their descriptions, and Docker instructions.
    Also includes explanations in English.
    """
    help_text = """
## **Met Museum Artifact Scraper**

This script scrapes artifact data from the Metropolitan Museum of Art website.

### **Available Commands:**

| Command | Description | Description in English                                                                                                                               |
|---|---|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| `run` | Executes the main scraping process. | Executes the main scraping process.                                                                                                                    |
| `help` | Displays this help message with available commands and Docker instructions. | Displays this help message with available commands, their descriptions, and Docker instructions.                                                    |

---

### **Functions:**

| Function                                     | Description                                                                               | Description in English                                                                                                                                 |
|----------------------------------------------|-------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `process_page(proxy, count_page, pbar)`      | Fetches and processes a specific page of artifacts.                                        | Fetches and processes a specific page of artifacts, extracting details and downloading related images.                                            |
| `get_session(proxy)`                         | Creates and returns a requests.Session object configured with the provided proxy.          | Creates and returns a requests.Session object configured with the provided proxy settings for making HTTP requests.                                   |
| `setup_logging()`                            | Configures and returns a logger for logging application messages.                           | Configures and returns a logger for logging application messages, including errors, warnings, and informational messages.                            |
| `handle_interrupt(signal_received, frame)`   | Handles interruptions (e.g., Ctrl+C) gracefully, ensuring data is saved.                   | Handles interruptions (e.g., Ctrl+C or SIGINT) gracefully, ensuring that any data being processed is saved before the script exits.                |
| `main()`                                     | Entry point of the application. Manages concurrent page processing using ThreadPoolExecutor. | Entry point of the application. Manages concurrent processing of multiple pages using ThreadPoolExecutor to speed up the data fetching process.   |
| `load_config(config_path="config.yaml")`     | Loads the configuration from a YAML file.                                                 | Loads the configuration settings from a YAML file (default: `config.yaml`), setting up parameters like URLs, headers, proxies, etc.              |
| `create_gitignore(folder_path)`              | Creates a .gitignore file in the specified folder.                                       | Creates a .gitignore file in the specified folder to ignore all files except the .gitignore itself, useful for excluding downloaded images from Git. |

---

### **Docker Instructions:**

1. **Build the Docker image:**

    ```bash
    docker-compose build
    ```

2. **Start the container in detached mode:**

    ```bash
    docker-compose up -d
    ```

3. **Execute the script inside the container:**
    *   **Using the `run` command:**
        ```bash
        docker exec -it metmuseum_scraper python Main_v4.py run
        ```
    *   **Using the `help` command:**
    ```bash
        docker exec -it metmuseum_scraper python Main_v4.py help
    ```
    **Note:** Replace `metmuseum_scraper` with the actual name of your container if it's different. You can find the container name using `docker ps`.

---

### **Example Usage (without Docker):**

1. **To run the scraper:**

    ```bash
    python Main_v4.py run
    ```

2. **To see this help message:**

    ```bash
    python Main_v4.py help
    ```

---

**Important Notes:**

*   The script uses multiple proxies to avoid being blocked. (Uses multiple proxies to avoid IP blocking)
*   Logs are saved in the `Logs` directory. (Logs are saved in the directory specified in `config.yaml` or `Logs` by default)
*   Scraped data (JSON and images) is saved in the `Save_Data/Arts_Data` directory. (Scraped data, including JSON files and images, is saved in the directory specified in `config.yaml` or `Save_Data/Arts_Data` by default)
*   The script handles interruptions gracefully. Press Ctrl+C to stop it, and it will save the progress. (Handles interruptions like Ctrl+C gracefully. Press Ctrl+C to stop, and it will attempt to save current progress)
*   Make sure you have Docker and Docker Compose installed if you want to use the Docker method. (Ensure Docker and Docker Compose are installed for Docker usage)
*   Configuration is loaded from `config.yaml`. (Configuration parameters are loaded from `config.yaml`)
*   Each folder with images will have a .gitignore file to prevent accidental commits of images to a Git repository. (A .gitignore file is created in each image folder to prevent images from being tracked by Git)
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