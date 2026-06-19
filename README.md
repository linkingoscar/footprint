# 足迹 - 记录你的美好生活

> **[English](README.en.md)**

一个现代化的个人足迹记录网站，围绕照片资源展开，借助地图API匹配照片地理信息，记录旅行、美食、情侣三大场景。

## ✨ 核心功能

### 照片 + 地图核心
- 📍 **EXIF智能定位** - 上传照片自动提取GPS坐标，标记到地图
- 🗺️ **足迹地图** - 在地图上查看所有记录，点击查看详情
- 🛤️ **轨迹回放** - 按时间顺序动画回放旅行路线
- 📅 **时间线** - 按月份分组展示记录，照片瀑布流
- 📊 **统计报告** - 月度趋势、去过的地方、照片数量

### 三大记录模式

| 模式 | 功能 |
|------|------|
| ✈️ **旅行记录** | 足迹地图、旅行相册、成就徽章、天气查询、行程规划、费用记录 |
| 🍜 **美食打卡** | 美食地图、餐厅打卡、美食评分、分类标签、价格记录、食材追踪 |
| 💑 **情侣足迹** | 爱情地图、情侣日记、纪念日、爱情笔记、约会计划、在一起天数 |

### 通用功能
- 📷 **多方式上传** - 本地文件/文件夹拖拽、相册选择、URL链接、批量上传
- 🗺️ **多地图支持** - 高德/百度/腾讯/必应地图API可选
- ☁️ **云存储支持** - 阿里云OSS/腾讯云COS/七牛云/AWS S3/Google Cloud/Azure
- 🌙 **明暗模式** - 深色/浅色主题切换
- 🌐 **多语言** - 中文/英文界面切换
- 📱 **PWA支持** - 可安装到手机桌面，支持离线使用
- ✨ **粒子背景** - 动态粒子效果，跟随主题色变化

## 🚀 快速开始

### 方式一：纯前端模式（推荐）

无需后端服务，直接打开HTML文件：

```powershell
# 1. 打开设置页面配置API Key
frontend/settings.html

# 2. 打开主页开始使用
frontend/index.html
```

### 方式二：完整服务模式

```powershell
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动后端
cd backend
python app.py

# 3. 访问 http://localhost:5000
```

### 方式三：Docker部署

```powershell
# 构建并启动
docker-compose up -d

# 访问 http://localhost:5000（直连 Flask）或 http://localhost（Nginx）
```

## 📁 项目结构

```
footprint/
├── frontend/                    # 前端页面
│   ├── index.html              # 主页
│   ├── settings.html           # 设置页面
│   ├── guide.html              # 使用指南
│   ├── manifest.json           # PWA配置
│   └── sw.js                   # Service Worker
│
├── backend/                     # 后端服务
│   ├── app.py                  # Flask主程序
│   ├── database.py             # 数据库模型
│   ├── exif_extractor.py       # EXIF提取
│   ├── ocr_processor.py        # OCR处理
│   └── uploads/                # 上传文件存储
│
├── miniapp/                     # 微信小程序
├── tests/                       # 测试文件
├── docs/                        # 文档
├── nginx/                       # Nginx配置
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🗺️ 地图API配置

支持四种地图服务，任选其一：

| 地图服务 | 申请地址 | 适用场景 |
|----------|----------|----------|
| 🇨🇳 高德地图 | [lbs.amap.com](https://lbs.amap.com/) | 国内首选 |
| 🇨🇳 百度地图 | [lbsyun.baidu.com](https://lbsyun.baidu.com/) | POI丰富 |
| 🇨🇳 腾讯地图 | [lbs.qq.com](https://lbs.qq.com/) | 微信生态 |
| 🌍 必应地图 | [bingmapsportal.com](https://www.bingmapsportal.com/) | 全球覆盖 |

## ☁️ 云存储配置

支持国内外主流云存储服务：

### 国内服务
| 服务 | 申请地址 | 特点 |
|------|----------|------|
| 阿里云OSS | [aliyun.com/oss](https://www.aliyun.com/product/oss) | 国内主流 |
| 腾讯云COS | [cloud.tencent.com/cos](https://cloud.tencent.com/product/cos) | 微信生态 |
| 七牛云 | [qiniu.com](https://www.qiniu.com/) | CDN加速 |

### 国外服务
| 服务 | 申请地址 | 特点 |
|------|----------|------|
| AWS S3 | [aws.amazon.com/s3](https://aws.amazon.com/s3/) | 全球领先 |
| Google Cloud | [cloud.google.com/storage](https://cloud.google.com/storage) | AI集成 |
| Azure Blob | [azure.microsoft.com/storage](https://azure.microsoft.com/en-us/products/storage/blobs/) | 企业级 |

## 🛠️ 技术栈

- **前端**: HTML/CSS/JavaScript（单文件，无构建）
- **地图**: 高德/百度/腾讯/必应 JS API
- **粒子**: tsParticles
- **后端**: Python Flask
- **数据库**: SQLite/PostgreSQL
- **存储**: localStorage/阿里云OSS/腾讯云COS/七牛云/AWS S3/Google Cloud/Azure Blob
- **部署**: Docker/Nginx

## 📱 平台支持

| 平台 | 支持 |
|------|------|
| Web浏览器 | ✅ Chrome/Firefox/Safari/Edge |
| PWA | ✅ 可安装到桌面 |
| iPhone | ✅ Safari全屏支持 |
| Android | ✅ Chrome安装支持 |
| 微信小程序 | ✅ 基础结构已就绪 |

## 📄 许可证

MIT License
