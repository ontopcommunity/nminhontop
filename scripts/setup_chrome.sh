#!/bin/bash
set -e
pip install -q selenium
python3 -c "from selenium import webdriver; from selenium.webdriver.chrome.options import Options; o=Options(); o.add_argument("--headless=new"); o.add_argument("--no-sandbox"); o.add_argument("--disable-dev-shm-usage"); o.binary_location="/usr/bin/google-chrome"; d=webdriver.Chrome(options=o); print("OK"); d.quit()"
