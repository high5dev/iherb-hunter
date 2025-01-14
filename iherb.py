import os
import csv
import time
import threading
import random
import json
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tkinter import ttk
import tkinter as tk
from tkinter import filedialog, messagebox
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

# Global variable to store selected folder
selected_folder = None


def configure_driver():
    """Configures and returns an undetected-chromedriver WebDriver."""
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")
    # options.add_argument("--disable-gpu")
    # options.add_argument("--disable-software-rasterizer")
    # options.add_argument("--disable-webgl")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(options=options)
    return driver


def bypass_press_and_hold(driver):
    """Bypass 'Press and Hold' modal dynamically, handling iframe and variations."""
    try:
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        driver.switch_to.frame(iframe)
        print("Switched to iframe.")

        press_hold_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'UhTVexkQJowzHLq') and @role='button']"))
        )
        ActionChains(driver).click_and_hold(press_hold_button).perform()
        print("Press and Hold action started.")

        time.sleep(5)
        ActionChains(driver).release(press_hold_button).perform()
        print("Press and Hold action released.")

        driver.switch_to.default_content()
        print("Switched back to default content.")

    except Exception as e:
        print(f"Error bypassing 'Press and Hold': {e}")


def save_cookies(driver, filename="cookies.json"):
    """Saves cookies to a file."""
    cookies = driver.get_cookies()
    with open(filename, "w") as file:
        json.dump(cookies, file)
    print(f"Cookies saved to {filename}")


def load_cookies(driver, filename="cookies.json"):
    """Loads cookies from a file."""
    if os.path.exists(filename):
        with open(filename, "r") as file:
            cookies = json.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)
        print(f"Cookies loaded from {filename}")
    else:
        print(f"Cookie file {filename} does not exist.")

def wait_for_element(driver):
    """Wait until the target div is fully loaded."""
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-description-title"))
        )
        print("Target element loaded successfully!")
    except TimeoutException:
        print("Timeout: Target element did not load.")

def scrape_iherb(category, page_range, save_folder, progress_bar, status_label):
    """Scrapes product data from iHerb."""
    driver = configure_driver()
    try:
        site_url = "https://www.iherb.com"
        start_page, end_page = map(int, page_range.split('-'))
        data = []
        total_pages = end_page - start_page + 1
        progress_bar["maximum"] = total_pages
        current_page = 0

        # Navigate and save cookies on the first search page
        full_url = f"{site_url}/search?kw={category}"
        print(f"Navigating to: {full_url}")
        driver.minimize_window()
        driver.get(full_url)

        # Save cookies after the first page load
        save_cookies(driver)

        # Attempt to click the "Accept All" cookie banner
        try:
            accept_all_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "truste-consent-button"))
            )
            accept_all_button.click()
            print("Clicked 'Accept All' on cookie banner.")
            time.sleep(2)
        except Exception:
            print("Cookie banner not found or could not be clicked.")

        for page_number in range(start_page, end_page + 1):
            if page_number != 1:
                full_url = f"{site_url}/search?kw={category}&p={page_number}"
                print(f"Navigating to: {full_url}")
                driver.get(full_url)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            product_links = [
                link["href"]
                for link in soup.select("div.absolute-link-wrapper a.absolute-link")
                if link["href"]
            ]
            print(f"Found {len(product_links)} product links on page {page_number}.")

            for link in product_links:
                driver.get(site_url)  # Navigate to the site base URL
                load_cookies(driver)  # Load cookies
                driver.minimize_window()
                driver.get(link)  # Navigate to the product page
                status_label.config(text=f"Navigating to: {link}")

                if "Please confirm your identity" in driver.page_source:
                    print("Detected 'Press and Hold'. Attempting to bypass...")
                    bypass_press_and_hold(driver)

                print(link)
                time.sleep(random.uniform(2, 5))
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "ugc-apollo")))
                wait_for_element(driver)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                product_summary_block = soup.find("section", class_="product-description-title")
                name = (
                    product_summary_block.find("h1").get_text(strip=True)
                    if product_summary_block and product_summary_block.find("h1")
                    else "N/A"
                )
                price = (
                    soup.find("div", class_="price-inner-text").text.strip()
                    if soup.find("div", "price-inner-text")
                    else "N/A"
                )
                desc_block = soup.find("div", "product-overview")
                description = (
                    desc_block.find("div", "inner-content").get_text(strip=True)
                    if desc_block and desc_block.find("div", "inner-content")
                    else "N/A"
                )
                data.append([name, description, price, link])

                status_label.config(text=f"Scraped product: {name}")
                root.update_idletasks()

            current_page += 1
            progress_bar["value"] = current_page
            root.update_idletasks()

        save_to_csv(save_folder, data, ["Name", "Description", "Price", "Link"])
        status_label.config(text="Scraping complete! Check the output folder.")
    finally:
        driver.quit()


def save_to_csv(folder, data, headers):
    """Saves data to a CSV file."""
    if not folder:
        folder = os.getcwd()
    csv_file = os.path.join(folder, "iherb_products.csv")
    with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(data)
    print(f"Data saved to {csv_file}")


def select_folder():
    """Opens a folder selection dialog."""
    global selected_folder
    selected_folder = filedialog.askdirectory()
    if selected_folder:
        messagebox.showinfo("Folder Selected", f"Files will be saved in: {selected_folder}")
    else:
        messagebox.showinfo(
            "No Folder Selected", "Files will be saved in the script's directory."
        )


def start_scraping_thread():
    """Starts the scraping process in a separate thread."""
    category = category_scrape_entry.get()
    page_range = page_range_scrape_entry.get()

    if not category or not page_range:
        messagebox.showwarning("Input Error", "Please fill all fields.")
        return

    try:
        # Validate the page range format
        start_page, end_page = map(int, page_range.split("-"))
        if start_page <= 0 or end_page < start_page:
            raise ValueError
    except ValueError:
        messagebox.showerror("Input Error", "Page range must be a valid numeric range (e.g., '1-5').")
        return

    progress_bar["value"] = 0
    status_label.config(text="Starting the scraping process...")
    threading.Thread(
        target=scrape_iherb,
        args=(category, page_range, selected_folder, progress_bar, status_label),
        daemon=True,
    ).start()


# Set up Tkinter GUI
root = tk.Tk()
root.title("iHerb Scraper")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

ttk.Label(frame, text="Enter Product Category:").grid(row=0, column=0, sticky=tk.W)
category_scrape_entry = ttk.Entry(frame, width=50)
category_scrape_entry.grid(row=0, column=1, sticky=tk.E)

ttk.Label(frame, text="Enter Page Range (e.g., 1-5):").grid(row=1, column=0, sticky=tk.W)
page_range_scrape_entry = ttk.Entry(frame, width=20)
page_range_scrape_entry.grid(row=1, column=1, sticky=tk.E)

ttk.Button(frame, text="Select Folder", command=select_folder).grid(row=2, column=0, sticky=tk.W)
ttk.Button(frame, text="Scrape", command=start_scraping_thread).grid(row=2, column=1, sticky=tk.E)

progress_bar = ttk.Progressbar(frame, orient="horizontal", length=400, mode="determinate")
progress_bar.grid(row=3, column=0, columnspan=2, pady=10)

status_label = ttk.Label(frame, text="")
status_label.grid(row=4, column=0, columnspan=2, sticky=tk.W)

root.mainloop()
