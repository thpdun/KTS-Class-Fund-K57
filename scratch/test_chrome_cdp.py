import subprocess
import json
import time
import urllib.request
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
print("Chrome exists:", os.path.exists(chrome_path))

# Test launching Chrome headless with remote debugging
proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9222",
    "--disable-gpu",
    "--no-sandbox"
])

time.sleep(2)
try:
    with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=5) as response:
        data = json.loads(response.read().decode())
        print("Chrome CDP Version:", data)
finally:
    proc.terminate()
    proc.wait()

