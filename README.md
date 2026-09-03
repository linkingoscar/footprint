# 🧭 足迹 Footprint · 记录你的山海与寻味之旅

<div align="center">

[![Release](https://img.shields.io/badge/Release-v1.0.3-emerald.svg)](https://github.com/linkingoscar/footprint)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Three.js](https://img.shields.io/badge/WebGL-Globe.gl-000000?logo=three.dot.js&logoColor=white)](https://globe.gl/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900?logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![PWA](https://img.shields.io/badge/PWA-Ready-5A0FC8?logo=pwa&logoColor=white)](https://web.dev/progressive-web-apps/)
[![i18n](https://img.shields.io/badge/i18n-中英双语-0EA5E9)](#)
[![Design](https://img.shields.io/badge/Design-Swiss_Aesthetic-D97706)](#)

<p align="center">
  <strong>聚焦“旅行探索 + 美食寻味”的高颜值生活方式足迹记录平台</strong><br>
  内置 1/4/9 宫格多图排版 · 奢华时光轨迹时间轴 · 3D WebGL 点亮地球 · 通关护照印章册 · 真实双人情侣协同空间 · 免安装离线桌面双模驱动
</p>

[✨ 功能亮点](#-核心功能亮点) •
[🚀 快速上手](#-快速上手) •
[🍃 本地伪应用模式](#-纯本地免装桌面伪应用) •
[🎨 美学规范](#-去-ai-塑料感与大地美学) •
[🏗️ 架构底座](#-系统架构与二次开发) •
[📑 API 文档](docs/API.md)

</div>

---

## 📖 产品理念与定位

在日常记录中，**旅行**与**美食**天然互为映衬，构成了每个人最值得珍藏的生活探索印迹。

**足迹 Footprint** 将主页永远聚焦于“旅行探索 + 美食寻味”两大核心场景；而**情侣模式**则收敛在管理后台作为增值协同层——开启并完成 6 位浪漫配对后，主页将动态点亮情侣专属工具组与双人甜蜜标记，实现**一人打卡、双向实时同步**，关闭时不影响任何基础数据。

---

## ✨ 核心功能亮点

### 1. 📸 1、4、9 宫格多图自适应排版与纵向相册流 (`MosaicEngine`)
- **多图动态排版引擎**：根据上传照片数量智能呈现 **1 图画卷、4 图精致田字格、9 图九宫格**；超过 9 张时自动呈现 `+N` 剩余张数遮罩角标与 `📷 N图` 专属徽章。
- **纵向沉浸式故事相册流**：点开足迹卡片后，支持自顶向下顺畅滑动浏览完整高分辨率图集，每张图片自带当前序列（`1 / 4`），带来媲美优质手账画报的沉浸感。

### 2. 🎞️ 奢华流光时光轨迹轴 (`LuxuryTimeline`)
- **流光渐变垂直时间轴**：按时间倒序将所有旅途足迹与美食回忆连缀成线。
- **按月里程碑归档**：以浮动月度标签区分光阴节点，结合类别专属微光节点（旅行天蓝、美食暖金、情侣粉桃）与横向胶片感缩略图预览。

### 3. 🪐 3D WebGL 交互点亮地球与微光亮点 (`GlobeConquest`)
- **双重视角平滑切换**：
  - **🇨🇳 默认国内深度视角**：城市打卡呈现 3D 浮雕立体高光与一闪一闪的星空微光打卡亮点，告别生硬连线；
  - **🌐 Global 全球旅行视角**：一键飞升太空全景，世界 177+ 国家多边形染色，海外足迹自动点亮对应国家版图。
- **瑞士排版征服看板**：实时精确统计点亮城市数、覆盖省份百分比与迁徙足迹。

### 4. 🛂 虚拟旅行通关护照与海关印章墙 (`PassportModule`)
- 赋予每座到访城市一枚**海关入境戳质感的专属复古印章**；
- 具备城市航空三字码（`PEK`, `SHA`, `HGH`, `CAN`, `CTU` 等）、中英文地名、首次入境日期、等宽经纬度坐标与微倾斜印泥质感，以复古羊皮纸内页呈现。

### 5. 🎖️ 旅行家 8 阶成就勋章体系 (`BadgesModule`)
- 初级漫游者、山海拾遗人、深夜食堂探索官、挑剔寻味家、快门收藏家、浪漫同游人、版图征服家、百川归海旅行家；
- 阶梯式进度条与解锁撒花正反馈。

### 6. 🎲 “今天吃什么”寻味轮盘与自定义加菜 (`FoodWheel`)
- 专治选择困难症！优先提取个人足迹中打卡的高分探店美食（⭐>=4），物理减速回弹与粒子彩带礼花；
- **支持自由新增自定义私房菜**，提供 10 大快捷灵感气泡（烤肉、火锅、日料、轻食等），金标专属持久化存储。

### 7. ⚡ 3 秒极速闪录与剪贴板直接粘贴 (`QuickCatch`)
- **全局图片剪贴板粘贴 (`Ctrl+V`)**：截屏或复制照片后唤出弹窗即可一键粘贴导入；
- **拖拽智能解析**：拖入照片时自动提取 EXIF GPS 经纬度，自动逆地理编码推断行政区商圈地名，自动拟定标题并回填日期；
- **网络直链批量导入**：支持单张图床链接与多行 URL 文本批量解析导入。

### 8. 🌐 全场景深度中英双语国际化 (`i18n`)
- 一键无缝切换中英文，从顶栏导航、模式胶囊、4 大展馆、工具 Dock，到快速统计、添加弹窗及详情卡片标签，实现 100% 动态即时双语自适应。

### 9. 🧳 灵动生活实用微组件与美化后台
- **出游防漏行李清单 (`PackingListModule`)**：分类清单、完成度打勾与自定义扩充；
- **寻味食材库 (`Ingredients`)**：私房备料库，带有蔬菜菌菇、优质肉禽等分类灵感气泡；
- **甜蜜情感空间 (`LoveCapsuleModule`)**：6 位邀请码浪漫配对、大日子倒数日、恋爱手账便签、约会日程清单与心愿达成进度条。
- **后台毛玻璃分段控制**：告别突兀大色块，采用珊瑚玫瑰渐变高亮与精致数据看板。

---

## 🎨 去“AI 塑料感”与大地美学

本项目坚决拒绝市面上 AI 模板泛滥的蓝紫荧光渐变（`#8b5cf6 -> #ec4899`）与参差不齐的彩色 Emoji：
- **旷野大地色彩体系**：黑曜石夜色（`#0B0E14`, `#151A24`）、冷杉青绿（`#0D9488`）、探索暖琥珀（`#D97706` / `#F59E0B`），浅色模式转向温润羊皮纸白（`#F8F6F0`）；
- **Lucide 纯矢量 SVG 图标库 (`frontend/js/icons.js`)**：全站关键交互节点全面换装 24x24 黄金比例单色矢量线条，100% 离线内置，永无加载白屏；
- **瑞士国际平面排版**：大比例悬殊字重、Monospace 等宽坐标与呼吸感克制边框。

---

## 🍃 纯本地免装桌面“伪应用”

即使你**未安装 Python、没有启动任何后端、甚至处于断网环境**，系统底层搭载的 `LocalFallbackEngine` 会自动无缝承接所有读写：
- 所有的足迹增删改查、配置、3D 地球、通关护照、清单均完整保存在本机浏览器持久化存储中；
- 拖入照片时自动进行本地安全压缩（Base64 Data URL），**完全脱离后端上传服务依然永久可用**；
- 电脑解压即可秒开使用，具备极高隐私安全性。

---

## 🚀 快速上手

### 方式 1：Windows 桌面一键启动（免配置推荐）
直接双击运行根目录下的脚本：
```cmd
启动足迹-本地模式.bat
```
*注：脚本自动检测环境，有 Python 则启动云端全栈服务，无 Python 则直接拉起纯本地离线桌面模式！*

### 方式 2：本地 Python 全栈服务
```bash
# 1. 克隆代码
git clone https://github.com/linkingoscar/footprint.git
cd footprint

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python app.py

# 4. 浏览器访问
open http://localhost:5000
```

### 方式 3：Docker 生产容器编排
```bash
docker-compose up -d --build
```

---

## 📁 目录结构

```
footprint/
├── 启动足迹-本地模式.bat    # Windows 桌面一键启动器
├── app.py                  # 服务端入口
├── requirements.txt        # 依赖清单
├── frontend/               # 前台应用宿主 (单页 Web 应用)
│   ├── index.html          # 主页 (旅行 + 美食核心足迹)
│   ├── admin.html          # 网页管理后台 (排版/足迹CMS/数据库图床脚手架)
│   ├── settings.html       # 系统设置与偏好配置
│   ├── css/                # 样式系统 (base.css, layout.css, components.css)
│   └── js/                 # 模块化业务脚本 (globe, passport, icons, etc.)
├── backend/                # 后端服务
│   ├── database.py         # 存储驱动 (SQLite, PostgreSQL, JSON)
│   ├── storage.py          # 对象存储 (Local, Aliyun OSS, Tencent COS, S3)
│   ├── auth.py             # JWT 鉴权体系
│   └── routes/             # 业务蓝图 (records, couple, admin, features, etc.)
├── docs/                   # 核心文档
│   ├── ARCHITECTURE.md     # 系统全栈架构设计与二次开发底座指南
│   └── API.md              # RESTful API 完整规范手册
└── tests/                  # 自动化测试套件 (67 项自动化测试 100% 覆盖)
```

---

## 🏗️ 系统架构与二次开发

本项目设计了高度解耦的微内核抽象，非常适合作为底座进行二次开发扩展（如新增宠物日记、户外露营装备清单、骑行轨迹等）。

详细的分层拓扑、数据流向图、双模降级原理与标准化二次开发示例请查阅：
👉 **[全栈架构设计与二次开发底座指南 (docs/ARCHITECTURE.md)](docs/ARCHITECTURE.md)**

---

## 🧪 测试与质量保证

全套自动化测试套件通过率 100%：
```bash
python -m pytest tests/ -v
# 67 passed in 15.89s
```

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 协议开源，欢迎自由体验、二次开发与个人定制！
