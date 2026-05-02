import subprocess
import sys

scripts = [
    "scripts/scraper_davis.py",
    "scripts/scraper_toptextil.py",
    "scripts/scraper_litena.py",
    "scripts/enrich_types.py"
]

for script in scripts:
    print(f"\n{'='*50}\nRUNNING: {script}\n{'='*50}\n")
    try:
        subprocess.run([sys.executable, script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script}: {e}")
        
print("\nFINISHED ALL.")
