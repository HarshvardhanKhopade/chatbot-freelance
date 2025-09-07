import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
new_dir = os.path.join(BASE_DIR, "chatbot", "templates", "chatbot")
os.makedirs(new_dir, exist_ok=True)

# Galat folder ka path (with space)
wrong_dir = os.path.join(BASE_DIR, "chatbot", "templates chatbot")
old_file = os.path.join(wrong_dir, "chatbot.html")
new_file = os.path.join(new_dir, "chatbot.html")

if os.path.exists(old_file):
    os.rename(old_file, new_file)
    print(f"✅ Moved: {old_file} → {new_file}")
else:
    print("⚠️ Old file not found at", old_file)

print(f"✅ Templates directory ready at: {new_dir}")
