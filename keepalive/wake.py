"""Keep the Streamlit Community Cloud app awake.

Community Cloud apps sleep after inactivity. A plain HTTP ping (e.g. UptimeRobot)
only fetches the sleep page — it does NOT click the "Yes, get this app back up!"
button, so the app stays asleep. This script drives headless Chrome to actually
click that button. It runs on a schedule from GitHub Actions (see wake.yml).
"""

from __future__ import annotations

import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

APP_URL = os.environ.get("STREAMLIT_APP_URL", "https://badboy.streamlit.app/")
# Match the wake button by its text (robust to nested <span> markup).
WAKE_XPATH = "//button[contains(., 'get this app back up')]"


def main() -> None:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Selenium 4 auto-resolves chromedriver via Selenium Manager — no extra deps.
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(APP_URL)
        print(f"Opened {APP_URL}")

        wait = WebDriverWait(driver, 20)
        try:
            button = wait.until(EC.element_to_be_clickable((By.XPATH, WAKE_XPATH)))
            print("Sleep screen detected — clicking the wake button…")
            button.click()
            try:
                wait.until(EC.invisibility_of_element_located((By.XPATH, WAKE_XPATH)))
                print("Wake button clicked; the app is starting up ✅")
            except TimeoutException:
                print("Clicked, but the button is still visible ❌")
                raise SystemExit(1)
        except TimeoutException:
            # No button means Streamlit never showed the sleep screen.
            print("No sleep screen found — the app is already awake ✅")
    finally:
        driver.quit()
        print("Done.")


if __name__ == "__main__":
    main()
