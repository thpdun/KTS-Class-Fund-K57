import subprocess
import json
import time
import urllib.request
import tempfile
import websocket # let's check if websocket is available or we use http CDP endpoints
import os

try:
    import websocket
    print("websocket client available")
except ImportError:
    print("websocket not installed, let's check")

