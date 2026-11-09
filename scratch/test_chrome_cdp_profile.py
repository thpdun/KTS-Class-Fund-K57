import subprocess
import json
import time
import urllib.request
import tempfile

temp_dir = tempfile.mkdtemp()
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9222",
    f"--user-data-dir={temp_dir}",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check"
])

for i in range(10):
    time.sleep(0.5)
    try:
        with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=1) as response:
            data = json.loads(response.read().decode())
            print("SUCCESS! Chrome CDP Version:", data['Browser'])
            break
    except Exception as e:
        pass
else:
    print("Failed to connect after 5s")

proc.terminate()
proc.wait()

