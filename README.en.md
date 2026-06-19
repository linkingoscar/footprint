# Footprint — Record Your Beautiful Life

A modern personal footprint recording website centered around photos, using map APIs to match photo geolocation, covering three major scenarios: Travel, Food, and Couples.

> **[中文文档](README.md)**

---

## Core Features

### Photo + Map Core
- **EXIF Smart Positioning** — Auto-extract GPS coordinates from uploaded photos, mark on map
- **Footprint Map** — View all records on the map, click for details
- **Track Playback** — Animate travel routes in chronological order
- **Timeline** — Display records grouped by month, photo waterfall layout
- **Statistics Report** — Monthly trends, places visited, photo counts

### Three Recording Modes

| Mode | Features |
|------|----------|
| **Travel Record** | Footprint map, travel albums, achievement badges, weather query, itinerary planning, expense tracking |
| **Food Check-in** | Food map, restaurant check-in, food ratings, category tags, price records, ingredient tracking |
| **Couple Footprint** | Love map, couple diary, anniversaries, love notes, date planning, days together counter |

### General Features
- **Multi-upload** — Local files/folders drag & drop, album selection, URL links, batch upload
- **Multi-map Support** — Amap / Baidu / Tencent / Bing Maps API options
- **Cloud Storage** — Alibaba Cloud OSS / Tencent Cloud COS / Qiniu / AWS S3 / Google Cloud / Azure
- **Dark/Light Mode** — Theme switching
- **Multi-language** — Chinese / English interface
- **PWA Support** — Installable to home screen, offline usage
- **Particle Background** — Dynamic particle effects, follows theme colors

---

## Quick Start

### Option 1: Pure Frontend Mode (Recommended)

No backend required, just open the HTML files:

```powershell
# 1. Open settings page to configure API Key
frontend/settings.html

# 2. Open main page to start using
frontend/index.html
```

### Option 2: Full Stack Mode

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start backend
cd backend
python app.py

# 3. Visit http://localhost:5000
```

### Option 3: Docker Deployment

```powershell
# Build and start
docker-compose up -d

# Visit http://localhost:5000 (direct Flask) or http://localhost (Nginx)
```

---

## Project Structure

```
footprint/
├── frontend/                    # Frontend pages
│   ├── index.html              # Main page
│   ├── settings.html           # Settings page
│   ├── guide.html              # User guide
│   ├── manifest.json           # PWA config
│   └── sw.js                   # Service Worker
│
├── backend/                     # Backend service
│   ├── app.py                  # Flask main app
│   ├── database.py             # Database models
│   ├── exif_extractor.py       # EXIF extraction
│   ├── ocr_processor.py        # OCR processing
│   └── uploads/                # File storage
│
├── miniapp/                     # WeChat Mini Program
│   ├── app.json                # Mini program config
│   ├── app.js                  # Entry logic
│   ├── app.wxss                # Global styles
│   ├── components/             # Components
│   ├── pages/                  # Pages
│   └── utils/                  # Utilities
│
├── tests/                       # Test files
├── docs/                        # Documentation
├── nginx/                       # Nginx config
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Map API Configuration

Supports four map services, choose one:

| Map Service | Registration | Best For |
|-------------|-------------|----------|
| Amap | [lbs.amap.com](https://lbs.amap.com/) | China primary |
| Baidu Maps | [lbsyun.baidu.com](https://lbsyun.baidu.com/) | Rich POI data |
| Tencent Maps | [lbs.qq.com](https://lbs.qq.com/) | WeChat ecosystem |
| Bing Maps | [bingmapsportal.com](https://www.bingmapsportal.com/) | Global coverage |

---

## Cloud Storage Configuration

### Domestic (China)
| Service | Registration | Features |
|---------|-------------|----------|
| Alibaba Cloud OSS | [aliyun.com/oss](https://www.aliyun.com/product/oss) | China mainstream |
| Tencent Cloud COS | [cloud.tencent.com/cos](https://cloud.tencent.com/product/cos) | WeChat ecosystem |
| Qiniu | [qiniu.com](https://www.qiniu.com/) | CDN acceleration |

### International
| Service | Registration | Features |
|---------|-------------|----------|
| AWS S3 | [aws.amazon.com/s3](https://aws.amazon.com/s3/) | Global leader |
| Google Cloud | [cloud.google.com/storage](https://cloud.google.com/storage) | AI integration |
| Azure Blob | [azure.microsoft.com/storage](https://azure.microsoft.com/en-us/products/storage/blobs/) | Enterprise-grade |

---

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=backend
```

---

## Deployment

### Docker

```bash
# Build image
docker build -t footprint .

# Run container
docker run -p 5000:5000 -v ./backend/uploads:/app/backend/uploads -v ./data:/app/data footprint

# Or use Docker Compose
docker-compose up -d
```

### Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /path/to/frontend;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:5000;
    }
}
```

---

## Tech Stack

- **Frontend**: HTML/CSS/JavaScript (single-file, no build step)
- **Maps**: Amap / Baidu / Tencent / Bing JS API
- **Particles**: tsParticles
- **Backend**: Python Flask
- **Database**: SQLite/PostgreSQL
- **Storage**: localStorage / Alibaba Cloud OSS / Tencent Cloud COS / Qiniu / AWS S3 / Google Cloud / Azure Blob
- **Deployment**: Docker / Nginx

---

## Platform Support

| Platform | Support |
|----------|---------|
| Web Browser | Chrome / Firefox / Safari / Edge |
| PWA | Installable to home screen |
| iPhone | Safari fullscreen support |
| Android | Chrome install support |
| WeChat Mini Program | Basic structure ready |

---

## Documentation

- [API Documentation](docs/API.md) — Backend API reference
- [User Guide](frontend/guide.html) — How to use
- [Settings Page](frontend/settings.html) — Configure API and storage

---

## License

MIT License
