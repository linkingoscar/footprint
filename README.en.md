# 🧭 Footprint · Cherish Your Travels & Culinary Odysseys

<div align="center">

[![Release](https://img.shields.io/badge/Release-v1.0.0-emerald.svg)](https://github.com/linkingoscar/footprint)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Three.js](https://img.shields.io/badge/WebGL-Globe.gl-000000?logo=three.dot.js&logoColor=white)](https://globe.gl/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900?logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![PWA](https://img.shields.io/badge/PWA-Ready-5A0FC8?logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![Design](https://img.shields.io/badge/Design-Swiss_Aesthetic-D97706)](#)

<p align="center">
  <strong>A modern lifestyle footprint logging platform focused on Travel & Food</strong><br>
  Built-in Dual-User Couple Space · 3D WebGL Globe Conquest · Virtual Passport Stamp Wall · Zero-Install Offline Desktop Mode
</p>

[✨ Highlights](#-feature-highlights) •
[🚀 Quick Start](#-quick-start) •
[🍃 Offline Desktop Mode](#-zero-backend-offline-desktop-mode) •
[🎨 Earth Aesthetic](#-anti-ai-design--earth-aesthetic) •
[🏗️ Architecture](#-architecture--extensibility) •
[📑 API Docs](docs/API.md) •
[中文文档](README.md)

</div>

---

## 📖 Philosophy & Positioning

In life, **Travel** and **Food** naturally complement each other, shaping our most memorable lifestyle journeys.

**Footprint** keeps its homepage perpetually focused on **Travel Exploration + Food Discovery** as its primary core. **Couple Mode** is intentionally positioned in the Admin Panel as a value-added collaborative layer. Once paired via a 6-digit romantic code, the homepage illuminates couple toolcards and mutual memories, syncing footprint data bidirectionally between both partners in real time, while keeping individual base data safe and intact.

---

## ✨ Feature Highlights

### 1. 🪐 3D WebGL Globe Conquest (`GlobeConquest`)
- **Dual Perspective Smooth Interpolation**:
  - **🇨🇳 Domestic Prefecture-City View (Default)**: Drills down into Chinese prefecture-level cities; visited city polygons rise into **3D warm amber reliefs (`polygonAltitude: 0.05`)**, accompanied by concentric radar pulses and flowing flight arcs;
  - **🌐 Global View**: One-click flight to space orbit, highlighting 177+ world countries based on overseas checkpoints.
- **Swiss Layout Conquest Dashboard**: Real-time stats on visited cities, provinces percentage, and migratory arcs.

### 2. 🛂 Virtual Passport & Retro Customs Stamp Wall (`PassportModule`)
- Transcends dry lists by bestowing a **customs entry stamp** on every visited city;
- Displays airport 3-letter codes (`PEK`, `SHA`, `HGH`, `CAN`, `CTU`, etc.), bilingual city names, first entry date, monospace coordinates, and realistic stamp tilt on vintage parchment pages.

### 3. 🎖️ Traveler 8-Tier Milestones & Badges (`BadgesModule`)
- Novice Wanderer, Mountain & Sea Collector, Midnight Diner, Discerning Gourmet, Shutter Collector, Romantic Companion, Territory Conqueror, and Grand Wanderer;
- Real-time milestone progress bars with celebratory confetti upon unlocking.

### 4. ⚡ 3-Second Quick-Catch Workflow (`QuickCatch`)
- Drag and drop photos to automatically extract EXIF GPS coordinates, reverse geocode commercial districts and landmarks, generate expressive titles, and autofill check-in dates.

### 5. 🎲 Food Decision Wheel ("What to Eat Today") (`FoodWheel`)
- Cures decision paralysis by drawing from your previously checked-in top-rated restaurants (⭐ >= 4) with dynamic deceleration physics and confetti.

### 6. 🧳 Travel Packing Checklist (`PackingListModule`)
- Categorized checklist covering travel documents, tech gadgets, clothing & hygiene, and emergency medical kits with progress tracking and one-click reset for future trips.

### 7. 💕 Dual-User Couple Space & Emotional Tools (`LoveCapsuleModule`)
- **6-Digit Pairing Codes**: Seamless pairing to bind dual-user shared spaces;
- **Milestone Countdowns**: Automated countdowns to round days (520, 1000 days) and anniversaries;
- **💌 Sweet Time Capsules**: Seal letters or memories to be unlocked on a specific future date;
- **100 Wishes Bucket List**: Interactive progress ring with instant confetti upon completion.

---

## 🎨 Anti-AI Design & Earth Aesthetic

Say goodbye to cheap, neon purple-blue gradients (`#8b5cf6 -> #ec4899`) and inconsistent OS emojis:
- **Wild Earth Palette**: Obsidian deep space (`#0B0E14`, `#151A24`), pine teal (`#0D9488`), exploration amber (`#D97706` / `#F59E0B`), and parchment white (`#F8F6F0`);
- **Lucide Pure Vector SVG Icons (`frontend/js/icons.js`)**: Uniform 24x24 golden ratio geometric strokes, 100% locally embedded without any external font dependencies or white-screen flickers;
- **Swiss International Typographic Style**: Expressive font weight contrasts, monospace coordinates, and disciplined micro-borders.

---

## 🍃 Zero-Backend Offline Desktop Mode

Even if you **have not installed Python, never launched a backend server, or are completely offline**, the client-side `LocalFallbackEngine` seamlessly handles all requests:
- All footprints, configuration, 3D globe, passport stamps, and checklists are persisted directly in your browser's local storage;
- Dragged photos are automatically compressed into local Base64 Data URLs, **operating indefinitely without any external server dependency**;
- Simply unzip and double-click to start recording with total privacy.

---

## 🚀 Quick Start

### Option 1: Windows One-Click Desktop Launcher (Zero-Install)
Double-click the script in the root directory:
```cmd
启动足迹-本地模式.bat
```
*Note: Automatically launches the full stack if Python is present, or opens the standalone offline desktop app if not!*

### Option 2: Full Stack Python Server
```bash
# 1. Clone repository
git clone https://github.com/linkingoscar/footprint.git
cd footprint

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch server (modular launch or root entrypoint)
python -m backend.app
# or: python app.py

# 4. Visit in browser
open http://localhost:5000
```

### Option 3: Docker Deployment
```bash
docker-compose up -d --build
```

---

## 📁 Repository Structure

```
footprint/
├── 启动足迹-本地模式.bat    # Windows desktop launcher
├── app.py                  # Main Flask entrypoint
├── requirements.txt        # Python dependencies
├── frontend/               # Single Page Application
│   ├── index.html          # Main UI (Travel & Food Core)
│   ├── admin.html          # Admin CMS (Layout, CMS, DB/Storage monitoring)
│   ├── settings.html       # Preferences & System Settings
│   ├── css/                # Styling (base.css, components.css, map.css, couple.css)
│   └── js/                 # Modular business scripts (globe, storage, i18n, replay, icons, etc.)
├── backend/                # Backend services
│   ├── database.py         # Multi-database drivers & cloud storage adapters (SQLite, Postgres, OSS, COS, S3)
│   ├── auth.py             # JWT authentication & scoped media token
│   ├── helpers.py          # Media processing, reverse geocoding & utility helpers
│   └── routes/             # Blueprints (records, couple, admin, features, etc.)
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md     # Architecture Blueprint & Secondary Development Guide
│   └── API.md              # RESTful API Specification Manual
└── tests/                  # Test suite (70+ unit & integration tests, pytest-cov monitored)
```

---

## 🏗️ Architecture & Extensibility

Footprint provides a cleanly decoupled micro-core abstraction, making it ideal as a foundation for secondary development (e.g., pet diaries, outdoor camping itineraries, cycling routes).

Read the complete guide:
👉 **[Architecture Design & Developer Guide (docs/ARCHITECTURE.md)](docs/ARCHITECTURE.md)**

---

## 🧪 Testing & Quality Assurance

Comprehensive automated test suite passing at 100%:
```bash
pytest tests/ -v --cov=backend --cov-report=term-missing
# 70+ passed with strict coverage threshold
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE). Contributions and personal customizations are warmly welcomed!
