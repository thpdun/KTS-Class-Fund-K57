# -*- coding: utf-8 -*-
from pathlib import Path
import py_compile

server_path = Path("backend/server.py")
content = server_path.read_text(encoding="utf-8")
if "logger = logging.getLogger" not in content:
    content = content.replace("import threading\n", "import threading\nimport logging\n\nlogger = logging.getLogger('kts.server')\n", 1)
    server_path.write_text(content, encoding="utf-8")
    print("Added logging and logger.")

py_compile.compile(str(server_path), doraise=True)
print("SUCCESS: py_compile passed!")

