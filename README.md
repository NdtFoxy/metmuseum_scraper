# Met Museum Artifact Scraper

This script scrapes artifact data from the Metropolitan Museum of Art website. It uses multiple proxies to avoid IP blocking, handles interruptions gracefully, and saves data in JSON format along with associated images.

## Features

-   Fetches artifact details and images from the Met Museum website.
-   Uses a pool of proxies to distribute requests and avoid IP bans.
-   Saves scraped data in structured JSON format.
-   Downloads and saves artifact images in separate folders per page.
-   Handles script interruptions (e.g., Ctrl+C) gracefully and saves progress.
-   Configurable via a `config.yaml` file.
-   Creates `.gitignore` files in image folders to prevent accidental commits to Git.
-   Comprehensive logging of the scraping process.
-   Docker support for easy setup and execution.

## Requirements

-   Python 3.9+
-   Docker (optional, but recommended)
-   Docker Compose (optional, but recommended)

## Installation

### Using Docker (Recommended)

1. **Build the Docker image:**

    ```bash
    docker-compose build
    ```

2. **Start the container in detached mode:**

    ```bash
    docker-compose up -d
    ```

### Manual Installation (without Docker)

1. **Install required Python packages:**

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The script is configured using a `config.yaml` file. Here's an example:

```yaml
url_base: "https://www.metmuseum.org/art/collection/search?showOnly=withImage&department=11"
headers:
  Accept: "*/*"
  User-agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
output_folder: "Save_Data/Arts_Data"
proxy_list:
  - {"ip": "s-18346.sp2.ovh", "port": 11001, "country_code": "CZ", "username": "jTphN8YKiI_0", "password": "kV7JwDpIJXuc"}
  - {"ip": "s-18346.sp2.ovh", "port": 11002, "country_code": "CZ", "username": "jTphN8YKiI_1", "password": "kV7JwDpIJXuc"}
  - {"ip": "s-18346.sp2.ovh", "port": 11003, "country_code": "CZ", "username": "jTphN8YKiI_2", "password": "kV7JwDpIJXuc"}
  - {"ip": "s-18346.sp2.ovh", "port": 11004, "country_code": "CZ", "username": "jTphN8YKiI_3", "password": "kV7JwDpIJXuc"}
  - {"ip": "s-18346.sp2.ovh", "port": 11005, "country_code": "CZ", "username": "jTphN8YKiI_4", "password": "kV7JwDpIJXuc"}
  - {"ip": "s-18346.sp2.ovh", "port": 11006, "country_code": "CY", "username": "jTphN8YKiI_5", "password": "kV7JwDpIJXuc"}
  - {"ip": "s-18346.sp2.ovh", "port": 11007, "country_code": "CY", "username": "jTphN8YKiI_6", "password": "kV7JwDpIJXuc"}
  - {"ip": "s-18346.sp2.ovh", "port": 11008, "country_code": "FR", "username": "jTphN8YKiI_7", "password": "kV7JwDpIJXuc"}
  - {"ip": "s-18346.sp2.ovh", "port": 11009, "country_code": "FR", "username": "jTphN8YKiI_8", "password": "kV7JwDpIJXuc"}
  - {"ip": "s-18346.sp2.ovh", "port": 11010, "country_code": "DK", "username": "jTphN8YKiI_9", "password": "kV7JwDpIJXuc"}
total_pages: 67
log_dir: "Logs"
log_level: "DEBUG"
log_format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
date_format: "%Y-%m-%d %H:%M:%S"
max_retries: 3
retry_delay: 5
min_request_delay: 1
max_request_delay: 3