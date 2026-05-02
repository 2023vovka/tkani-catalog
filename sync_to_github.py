import os
import subprocess
from datetime import datetime

SOURCE_DIR = r"F:\Антигравити ии\база даных ткани"
GITHUB_DIR = r"F:\Антигравити ии\база даных ткани\github каталог ткани"

def sync_files():
    print("Начинаем быстрое копирование измененных файлов...")
    
    # Используем системную утилиту robocopy для молниеносного копирования только измененных файлов.
    # /MIR - делает точную зеркальную копию (удаляет то, что было удалено в оригинале).
    # /XD - исключаем саму папку github, а также тяжелые системные папки.
    cmd = [
        "robocopy",
        SOURCE_DIR,
        GITHUB_DIR,
        "/MIR",
        "/XD", "github каталог ткани", "node_modules", ".venv", "venv", "__pycache__", ".git", ".gemini",
        "/XF", "*.pyc", ".env",
        "/NJH", "/NJS", "/NDL", "/NC", "/NS"  # Скрываем лишний системный текст
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    # Коды robocopy от 0 до 7 считаются успешными
    if result.returncode < 8:
        print("✅ Копирование завершено.")
    else:
        print("⚠️ Произошла непредвиденная ошибка при копировании.")

def push_to_github():
    print("\nСинхронизация с GitHub...")
    os.chdir(GITHUB_DIR)
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_message = f"Автоматическое обновление: {current_time}"
    
    # Добавляем все изменения в Git
    subprocess.run(["git", "add", "."])
    
    # Проверяем, есть ли вообще какие-то изменения для отправки
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    
    if not status.stdout.strip():
        print("✅ База и файлы уже актуальны. Нет новых изменений для отправки.")
        return

    # Если изменения есть, коммитим и пушим
    try:
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print("Выполняем отправку в облако (push)...")
        subprocess.run(["git", "push"], check=True)
        print("\n🚀 Успех! Все новые данные отправлены на GitHub.")
    except Exception as e:
        print(f"\n⚠️ Ошибка при отправке на GitHub: {e}")

if __name__ == "__main__":
    if not os.path.exists(GITHUB_DIR):
        print(f"Ошибка: папка {GITHUB_DIR} не найдена.")
    else:
        sync_files()
        push_to_github()
