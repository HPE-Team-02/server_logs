import os
import shutil

current_dir = "."

for entry in os.listdir(current_dir):
    path = os.path.join(current_dir, entry)
    
    # Skip .py files and .env file
    if os.path.isfile(path) and (entry.endswith(".py") or entry == ".env"):
        continue
    
    # Remove files (except .py and .env)
    if os.path.isfile(path):
        try:
            os.remove(path)
            print(f"Deleted file: {entry}")
        except Exception as e:
            print(f"Could not delete file {entry}: {e}")
    
    # Remove directories and their contents
    elif os.path.isdir(path):
        try:
            shutil.rmtree(path)
            print(f"Deleted folder: {entry}")
        except Exception as e:
            print(f"Could not delete folder {entry}: {e}")
