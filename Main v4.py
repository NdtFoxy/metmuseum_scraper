import os
import requests
import random
from bs4 import BeautifulSoup as bs
import json
import signal
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Подавление предупреждений
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Список прокси (можно расширить, если требуется)
proxy_list = [
    {"ip": "s-18346.sp2.ovh", "port": 11001, "country_code": "CZ", "username": "jTphN8YKiI_0", "password": "kV7JwDpIJXuc"},
    {"ip": "s-18346.sp2.ovh", "port": 11002, "country_code": "CZ", "username": "jTphN8YKiI_1", "password": "kV7JwDpIJXuc"},
    {"ip": "s-18346.sp2.ovh", "port": 11003, "country_code": "CZ", "username": "jTphN8YKiI_2", "password": "kV7JwDpIJXuc"},
    {"ip": "s-18346.sp2.ovh", "port": 11004, "country_code": "CZ", "username": "jTphN8YKiI_3", "password": "kV7JwDpIJXuc"},
    {"ip": "s-18346.sp2.ovh", "port": 11005, "country_code": "CZ", "username": "jTphN8YKiI_4", "password": "kV7JwDpIJXuc"},
    {"ip": "s-18346.sp2.ovh", "port": 11006, "country_code": "CY", "username": "jTphN8YKiI_5", "password": "kV7JwDpIJXuc"},
    {"ip": "s-18346.sp2.ovh", "port": 11007, "country_code": "CY", "username": "jTphN8YKiI_6", "password": "kV7JwDpIJXuc"},
    {"ip": "s-18346.sp2.ovh", "port": 11008, "country_code": "FR", "username": "jTphN8YKiI_7", "password": "kV7JwDpIJXuc"},
    {"ip": "s-18346.sp2.ovh", "port": 11009, "country_code": "FR", "username": "jTphN8YKiI_8", "password": "kV7JwDpIJXuc"},
    {"ip": "s-18346.sp2.ovh", "port": 11010, "country_code": "DK", "username": "jTphN8YKiI_9", "password": "kV7JwDpIJXuc"}
]

url_base = "https://www.metmuseum.org/art/collection/search?showOnly=withImage&department=11"
headers = {
    "Accept": "*/*",
    "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

output_folder = "Save_Data/Arts_Data"
json_folder = os.path.join(output_folder, "json")
os.makedirs(json_folder, exist_ok=True)

stop_execution = False

def handle_interrupt(signal_received, frame):
    global stop_execution
    print("\nScript interrupted. Saving progress...")
    stop_execution = True

signal.signal(signal.SIGINT, handle_interrupt)

def get_session(proxy):
    session = requests.Session()
    session.proxies = {
        "http": f"socks5://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}",
        "https": f"socks5://{proxy['username']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
    }
    return session

def process_page(proxy, count_page):
    # Добавим небольшую задержку, чтобы не перегружать сайт
    time.sleep(random.uniform(1, 3))

    url = url_base if count_page == 1 else f"{url_base}&offset={(count_page - 1) * 40}"
    page_json_path = os.path.join(json_folder, f"Page_{count_page}_data.json")

    if os.path.exists(page_json_path):
        print(f"Data for page {count_page} already exists. Skipping...")
        return

    session = get_session(proxy)

    try:
        req = session.get(url, headers=headers, verify=False, timeout=15)
        src = req.text
    except requests.RequestException as e:
        print(f"Error fetching page {count_page} using proxy {proxy['ip']}:{proxy['port']}: {e}")
        return

    soup = bs(src, "lxml")
    all_arts_hrefs = soup.find_all(class_="redundant-link_redundantlink__b5TFR")
    array = ["https://www.metmuseum.org" + item.get("href") for item in all_arts_hrefs]

    artifacts_data = []
    page_images_folder = os.path.join(output_folder, f"Page_{count_page}")
    os.makedirs(page_images_folder, exist_ok=True)

    for href in array:
        if stop_execution:
            print("Exiting gracefully.")
            break

        try:
            req = session.get(href, headers=headers, verify=False, timeout=15)
            page_src = req.text
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

                    try:
                        img_data = session.get(img_url, headers=headers, verify=False, timeout=15).content
                        with open(image_path, "wb") as img_file:
                            img_file.write(img_data)
                    except Exception as e:
                        print(f"Failed to save image {img_url}: {e}")

            artifacts_data.append(art_details)
        except Exception as e:
            print(f"Error processing artifact at {href}: {e}")

    if not stop_execution:
        with open(page_json_path, "w", encoding="utf-8") as file:
            json.dump(artifacts_data, file, indent=4, ensure_ascii=False)

    print(f"Page {count_page} is ready")

def main():
    total_pages = 67
    with ThreadPoolExecutor(max_workers=len(proxy_list)) as executor:
        futures = []
        page_counter = 1
        while page_counter <= total_pages:
          for i in range(len(proxy_list)):
            if page_counter <= total_pages:
                future = executor.submit(process_page, proxy_list[i], page_counter)
                futures.append(future)
                page_counter += 1

        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()