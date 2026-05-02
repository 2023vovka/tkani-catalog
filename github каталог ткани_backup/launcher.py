import os
import sys

# Patch for PyInstaller --noconsole mode
# Uvicorn logging requires sys.stdout to have an isatty() method.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import time
import threading
import webbrowser
import uvicorn
import socket

# We need to change the current working directory to the folder containing the executable.
# This ensures that sqlite:///./fabrics.db and relative paths work correctly.
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
    os.chdir(base_dir)

from backend.main import app

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def open_browser(delay=2):
    # Wait a bit for the server to start
    time.sleep(delay)
    webbrowser.open("http://localhost:8080/frontend/index.html")

if __name__ == "__main__":
    if is_port_in_use(8080):
        # Если сервер уже запущен в фоновом режиме, просто открываем браузер
        open_browser(delay=0)
        sys.exit(0)
    else:
        # Запускаем поток для открытия браузера
        threading.Thread(target=open_browser, daemon=True).start()
        
        # Запускаем сервер
        uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")
