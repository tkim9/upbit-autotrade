"""
Selenium script to capture full-page screenshot of Upbit exchange page.

Requirements:
- Python 3.7+
- Selenium (pip install selenium)
- Chrome/Chromium browser installed on your system
- ChromeDriver (will be auto-downloaded by webdriver-manager)

Installation:
1. pip install selenium webdriver-manager
2. Make sure Chrome/Chromium is installed on your system
3. Run this script: python upbit_screenshot.py

Note: This script requires a graphical environment or headless Chrome support.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from datetime import datetime


def setup_driver():
    """
    Set up and configure Chrome WebDriver with necessary options.
    Uses webdriver-manager to automatically download and manage ChromeDriver.

    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1280,720')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # Use webdriver-manager to automatically download and setup ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def take_full_page_screenshot(url, output_filename=None, width=1920):
    """
    Navigate to a URL and take a full-page screenshot.

    Args:
        url (str): The URL to capture
        output_filename (str, optional): Output filename for the screenshot.
                                        If None, generates timestamp-based name.
        width (int, optional): Width of the screenshot in pixels. Default is 1920.

    Returns:
        str: Path to the saved screenshot file
    """
    driver = None

    try:
        # Set up driver
        print("Setting up Chrome WebDriver...")
        driver = setup_driver()

        # Navigate to URL
        print(f"Navigating to {url}...")
        driver.get(url)

        # Wait for page to load
        print("Waiting for page to load...")
        time.sleep(5)  # Give time for dynamic content to load

        # Try to wait for a specific element (adjust selector as needed)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception as e:
            print(f"Warning: Timeout waiting for element: {e}")

        # Get page dimensions for full screenshot
        print("Calculating page dimensions...")
        # Use specified width but get full height
        # total_height = driver.execute_script("return document.body.scrollHeight") # lets comment this out for now.
        width = 1280
        total_height = 1080

        # Set window size to capture full page with specified width
        driver.set_window_size(width, total_height)

        print(f"Page dimensions: {width}x{total_height}")

        # Wait a bit for resize
        time.sleep(2)

        # Open the time period menu and select '1시간'
        print("Opening time period menu...")
        try:
            # Wait for the menu element to be clickable
            menu_xpath = '//*[@id="fullChartiq"]/div/div/div[1]/div/div/cq-menu[1]/span/cq-clickable'
            menu_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, menu_xpath))
            )
            menu_element.click()
            print("Menu opened successfully")

            # Wait a bit for the menu dropdown to appear
            time.sleep(1)

            # Find and click the '1시간' option
            # The element is wrapped in a <translate> tag with original="1 Hour"
            print("Looking for '1시간' option...")
            # Find the translate element with original="1 Hour", then get its parent clickable element
            translate_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//translate[@original='1 Hour']"))
            )
            # Get the parent element (the clickable container)
            one_hour_option = translate_element.find_element(By.XPATH, "./..")
            # Use JavaScript click to ensure it works (more reliable for complex UI elements)
            one_hour_option.click()
            print("Selected '1시간' option")

            # Wait for the chart to update after selecting the time period
            time.sleep(2)

            # Open the studies menu and select '볼린저 밴드' (Bollinger Bands)
            print("Opening studies menu for Bollinger Bands...")
            try:
                # Wait for the dropdown menu element to be clickable
                dropdown_xpath = '/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[3]'
                dropdown_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, dropdown_xpath))
                )
                dropdown_element.click()
                print("Studies menu opened successfully")

                # Wait a bit for the menu dropdown to appear
                time.sleep(1)

                # Find and click the '볼린저 밴드' (Bollinger Bands) option
                print("Looking for '볼린저 밴드' option...")
                bollinger_bands_xpath = '/html/body/div[1]/div[2]/div[3]/span/div/div/div[1]/div/div/cq-menu[3]/cq-menu-dropdown/cq-scroll/cq-studies/cq-studies-content/cq-item[14]'
                bollinger_bands_element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, bollinger_bands_xpath))
                )
                bollinger_bands_element.click()
                print("Selected '볼린저 밴드' option")

                # Wait for the chart to update after adding Bollinger Bands
                time.sleep(2)

            except Exception as e:
                print(f"Warning: Could not select '볼린저 밴드' from menu: {e}")
                print("Continuing with screenshot anyway...")

        except Exception as e:
            print(f"Warning: Could not select '1시간' from menu: {e}")
            print("Continuing with screenshot anyway...")

        # Generate filename if not provided
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"charts/upbit_screenshot_{timestamp}.png"

        # Ensure .png extension
        if not output_filename.endswith('.png'):
            output_filename += '.png'

        # Ensure charts directory exists
        os.makedirs("charts", exist_ok=True)

        # If output_filename doesn't start with charts/, add it
        if not output_filename.startswith("charts/"):
            output_filename = f"charts/{output_filename}"

        # Take screenshot
        print("Taking screenshot...")
        driver.save_screenshot(output_filename)

        print(f"Screenshot saved successfully: {output_filename}")


        return output_filename

    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {e}")
        raise

    finally:
        # Clean up
        if driver:
            print("Closing browser...")
            driver.quit()


def main():
    """
    Main function to test the screenshot functionality.
    """
    # Upbit exchange URL
    url = "https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-ADA"

    print("=" * 60)
    print("Upbit Exchange Screenshot Capture")
    print("=" * 60)
    print()

    try:
        # Take screenshot with custom filename
        output_file = take_full_page_screenshot(
            url=url,
            output_filename="charts/upbit_ada_exchange.png"
        )

        print()
        print("=" * 60)
        print("SUCCESS!")
        print(f"Screenshot saved to: {output_file}")
        print("=" * 60)

    except Exception as e:
        print()
        print("=" * 60)
        print("FAILED!")
        print(f"Error: {e}")
        print("=" * 60)


if __name__ == "__main__":
    main()