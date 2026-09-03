import sqlite3

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# اضافه کردن ستون meditation_music
try:
    cursor.execute("ALTER TABLE users ADD COLUMN meditation_music TEXT DEFAULT ''")
    print("✅ ستون meditation_music اضافه شد!")
except:
    print("⚠️ ستون قبلاً وجود داشت یا خطایی رخ داد.")

conn.commit()
conn.close()
print("✅ کار تمام شد!")