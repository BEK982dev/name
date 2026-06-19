# 🎬 Video Downloader Bot

YouTube va Instagram videolarini yuklovchi Telegram bot.

---

## 📋 Talablar

- Python 3.10+
- ffmpeg (video birlashtirish uchun)

---

## ⚙️ O'rnatish

### 1. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 2. ffmpeg o'rnatish

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
https://ffmpeg.org/download.html dan yuklab, PATH ga qo'shing.

**macOS:**
```bash
brew install ffmpeg
```

### 3. Bot tokenini sozlash

`bot.py` faylini oching va shu qatorni o'zgartiring:

```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
```

Yoki muhit o'zgaruvchisi orqali:

```bash
export BOT_TOKEN="1234567890:AABBcc..."
```

**Token olish uchun:** [@BotFather](https://t.me/BotFather) ga boring → `/newbot` yozing

### 4. Botni ishga tushirish

```bash
python bot.py
```

---

## 🤖 Bot imkoniyatlari

| Funksiya | Tavsif |
|----------|--------|
| 🔗 Link yuborish | YouTube / Instagram URL |
| 📊 Sifat tanlash | 144p, 360p, 480p, 720p, 1080p + hajmi |
| 💾 Tarix saqlash | Barcha yuklamalar SQLite da saqlanadi |
| 📁 Fayllar ro'yxati | /start bosganda ko'rinadi |
| 🔄 Qayta yuborish | Saqlangan videoni qayta olish |
| 🗑 O'chirish | Alohida yoki barchasi |

---

## 📁 Fayl tuzilmasi

```
video_bot/
├── bot.py          # Asosiy bot kodi
├── database.py     # SQLite baza
├── downloader.py   # yt-dlp orqali yuklash
├── requirements.txt
└── README.md
```

---

## 🚀 Server da ishlatish (ixtiyoriy)

### systemd service (Linux)

`/etc/systemd/system/videobot.service` faylini yarating:

```ini
[Unit]
Description=Video Downloader Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/video_bot
Environment=BOT_TOKEN=YOUR_TOKEN_HERE
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

So'ng:

```bash
sudo systemctl enable videobot
sudo systemctl start videobot
```

---

## ⚠️ Muhim

- Instagram uchun ba'zan login talab qilinadi — ommaviy postlar ishlaydi
- Telegram 50MB dan katta fayllarni qabul qilmaydi
- Juda katta videolar uchun Past sifat tanlang
"# name" 
"# name" 
"# name" 
"# name" 
