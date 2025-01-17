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

| Function                                 | Description                                                                                                                                              |
| :--------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `help_command()`                         | **Displays the help message, including available commands, descriptions, and instructions for using Docker.**                                            |
| `process_page(proxy, ...)`               | Fetches and processes a single page of artifacts, extracting details and downloading related images.                                                     |
| `get_session(proxy)`                     | Creates a `requests.Session` object configured with the provided proxy settings for making HTTP requests.                                                |
| `setup_logging()`                        | Configures and returns a logger for logging application messages, including errors, warnings, and informational messages.                                |
| `handle_interrupt(...)`                  | Handles interruptions (e.g., Ctrl+C or SIGINT) gracefully, ensuring that any data being processed is saved before the script exits.                      |
| `main()`                                 | Entry point of the application. Manages concurrent processing of multiple pages using `ThreadPoolExecutor` to speed up the data fetching process.        |
| `load_config(...)`                       | Loads the configuration settings from a YAML file (default: `config.yaml`), setting up parameters like URLs, headers, proxies, etc.                      |
| `create_gitignore(...)`                  | Creates a `.gitignore` file in the specified folder to ignore all files except the `.gitignore` itself, useful for excluding downloaded images from Git. |
| `log_event(...)`                         | Logs events (success, failure, etc.) with details.                                                                                                       |
| `analyze_logs(...)`                      | Analyzes log files to determine which pages have been processed or failed, allowing the script to resume from where it left off.                         |

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