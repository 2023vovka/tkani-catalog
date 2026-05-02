import os
import shutil

src_dir = os.path.abspath(os.path.dirname(__file__))
dest_dir = os.path.join(src_dir, "github каталог ткани")

if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

# Folders to copy
folders_to_copy = ["backend", "frontend", "fabric_images"]
for folder in folders_to_copy:
    src_path = os.path.join(src_dir, folder)
    dest_path = os.path.join(dest_dir, folder)
    if os.path.exists(src_path):
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(src_path, dest_path)

# Files to copy
files_to_copy = ["fabrics.db", "requirements.txt"]
for file in files_to_copy:
    src_path = os.path.join(src_dir, file)
    dest_path = os.path.join(dest_dir, file)
    if os.path.exists(src_path):
        shutil.copy2(src_path, dest_path)

# Fix frontend/app.js API_BASE
app_js_path = os.path.join(dest_dir, "frontend", "app.js")
if os.path.exists(app_js_path):
    with open(app_js_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace hardcoded localhost with relative path
    content = content.replace("const API_BASE = 'http://localhost:8080/api';", "const API_BASE = '/api';")
    
    with open(app_js_path, "w", encoding="utf-8") as f:
        f.write(content)

# Add uvicorn to requirements.txt if not present
req_path = os.path.join(dest_dir, "requirements.txt")
if os.path.exists(req_path):
    with open(req_path, "r", encoding="utf-8") as f:
        req_content = f.read()
    if "uvicorn" not in req_content:
        with open(req_path, "a", encoding="utf-8") as f:
            f.write("\nuvicorn\n")

# Create a Procfile for Render (optional but helpful)
procfile_path = os.path.join(dest_dir, "Procfile")
with open(procfile_path, "w", encoding="utf-8") as f:
    f.write("web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT\n")

# Create a start.sh script just in case
start_sh_path = os.path.join(dest_dir, "start.sh")
with open(start_sh_path, "w", encoding="utf-8") as f:
    f.write("#!/bin/bash\nuvicorn backend.main:app --host 0.0.0.0 --port $PORT\n")

print("Files prepared successfully in 'github каталог ткани'")
