# 足迹 API 文档

## 基础信息

- **Base URL**: `http://localhost:5000/api`
- **Content-Type**: `application/json`
- **字符编码**: UTF-8
- **认证**: 除特别说明外，所有端点均需携带 JWT Token（见 [认证](#认证authentication)）

## 目录

- [认证](#认证authentication)
- [健康检查](#健康检查)
- [记录管理](#记录管理)
- [图片上传](#图片上传)
- [地理编码](#地理编码)
- [运行时配置](#运行时配置)
- [统计数据](#统计数据)
- [费用追踪](#费用追踪)
- [数据导出](#数据导出)
- [城市统计](#城市统计)
- [AI 故事](#ai-故事)
- [批量照片上传](#批量照片上传)
- [错误响应](#错误响应)
- [环境变量](#环境变量)

---

## 认证(Authentication)

除 `POST /api/auth/register`、`POST /api/auth/login`、`GET /api/health` 外，所有 API 端点均要求携带有效 JWT Token。未认证请求返回 `401`：

```json
{
    "error": "未认证，请先登录",
    "code": 401
}
```

**认证方式:**

- 请求头：`Authorization: Bearer <token>`
- Token 有效期默认 24 小时，可通过环境变量 `JWT_EXPIRY_HOURS` 调整
- 签名密钥来自环境变量 `JWT_SECRET_KEY`（生产环境必须设置固定值；未设置时每次启动随机生成，重启后所有 Token 失效）

**受保护图片:**

`GET /uploads/<filename>` 提供上传的图片，同样受保护，支持两种认证方式：

- `Authorization: Bearer <token>` 请求头
- `?token=<jwt>` 查询参数（供前端 `<img>` 标签等无法携带请求头的场景使用）

**数据隔离:**

每个用户只能访问自己创建的记录、费用与配置；后端按用户 ID 过滤，无法跨用户读取或修改。

### POST /api/auth/register

注册新用户，成功后直接返回 Token。

**请求体:**
```json
{
    "username": "traveller",
    "password": "secret123"
}
```

- `username`: 必填，3-32 个字符
- `password`: 必填，至少 6 个字符

**响应:** `201 Created`
```json
{
    "message": "注册成功",
    "token": "<jwt>",
    "user": {
        "id": "a1b2c3d4...",
        "username": "traveller"
    }
}
```

**错误情况:**
- `400`: 用户名/密码为空、用户名长度不符合要求、密码少于 6 位
- `409`: 用户名已存在

### POST /api/auth/login

登录，校验用户名密码并返回 Token。

**请求体:** 同注册（`username` + `password`）

**响应:**
```json
{
    "token": "<jwt>",
    "user": {
        "id": "a1b2c3d4...",
        "username": "traveller"
    }
}
```

**错误情况:**
- `400`: 用户名或密码为空
- `401`: 用户名或密码错误

### GET /api/auth/me

获取当前登录用户信息。

**请求头:** `Authorization: Bearer <token>`

**响应:**
```json
{
    "user_id": "a1b2c3d4...",
    "username": "traveller"
}
```

**错误情况:**
- `401`: 未认证或 Token 无效

---

## 健康检查

### GET /api/health

检查服务是否正常运行。无需认证，供容器探针与前端使用。

**响应示例:**
```json
{
    "status": "ok",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "map_provider": "amap",
    "map_configured": true,
    "storage_provider": "local",
    "db_type": "sqlite"
}
```

---

## 记录管理

### GET /api/records

获取记录列表。

**查询参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| mode | string | 否 | 过滤模式: `travel`, `food`, `love` |

**响应示例:**
```json
[
    {
        "id": "abc123",
        "mode": "travel",
        "title": "北京旅行",
        "description": "参观了天安门",
        "location": "北京市天安门",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "date": "2024-01-15",
        "images": ["/uploads/abc123.jpg"],
        "createdAt": "2024-01-15T10:30:00.000Z"
    }
]
```

### GET /api/records/:id

获取单条记录。

**路径参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 记录ID |

**响应:** 同上

### POST /api/records

创建记录。

**请求体:**
```json
{
    "mode": "travel",
    "title": "北京旅行",
    "description": "参观了天安门",
    "location": "北京市天安门",
    "latitude": 39.9042,
    "longitude": 116.4074,
    "date": "2024-01-15",
    "images": ["data:image/jpeg;base64,..."]
}
```

**必填字段:**
- `mode`: 记录模式
- `title`: 标题

**响应:** 201 Created

### PUT /api/records/:id

更新记录。

**请求体:** 同创建，所有字段可选

**响应:** 200 OK

### DELETE /api/records/:id

删除记录。

**响应:**
```json
{
    "message": "删除成功"
}
```

### POST /api/records/import

批量导入记录。设置页导入 JSON 时会调用该接口；`replace=true` 会先清空后端现有记录。

**请求体:**
```json
{
    "replace": true,
    "records": [
        {
            "id": "record-1",
            "mode": "travel",
            "title": "北京旅行",
            "date": "2026-01-01",
            "images": []
        }
    ]
}
```

**响应:**
```json
{
    "message": "导入成功",
    "count": 1,
    "records": [...]
}
```

### DELETE /api/records

清空全部记录，并尝试删除关联的本地/云端图片。

**响应:**
```json
{
    "message": "清空成功",
    "count": 42
}
```

---

## 图片上传

### POST /api/upload

上传单张图片。

**请求:** `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 图片文件 |

**响应:**
```json
{
    "url": "/uploads/abc123.jpg",
    "filename": "abc123.jpg",
    "original_name": "photo.jpg",
    "storage_provider": "local",
    "storage_key": "abc123.jpg",
    "latitude": 39.9042,
    "longitude": 116.4074,
    "date_taken": "2024-01-15",
    "exif": {
        "latitude": 39.9042,
        "longitude": 116.4074
    },
    "image_info": {
        "width": 4032,
        "height": 3024,
        "format": "JPEG",
        "mode": "RGB"
    }
}
```

### POST /api/upload/batch

批量上传图片。

**请求:** `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| files | File[] | 是 | 多个图片文件 |

**响应:**
```json
[
    {
        "url": "/uploads/abc123.jpg",
        "filename": "abc123.jpg"
    }
]
```

### POST /api/validate-url

验证图片URL是否有效。

**请求体:**
```json
{
    "url": "https://example.com/image.jpg"
}
```

**响应:**
```json
{
    "valid": true,
    "url": "https://example.com/image.jpg",
    "content_type": "image/jpeg"
}
```

---

## 地理编码

### GET /api/geocode

地址转坐标。接口会按运行时配置或 `MAP_PROVIDER` 使用高德、百度、腾讯或必应地图。

**查询参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| address | string | 是 | 地址 |

**响应:**
```json
{
    "success": true,
    "provider": "amap",
    "latitude": 39.9042,
    "longitude": 116.4074,
    "formatted_address": "北京市东城区天安门广场",
    "province": "北京市",
    "city": "北京市",
    "district": "东城区"
}
```

### GET /api/reverse-geocode

坐标转地址。

**查询参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| lat | number | 是 | 纬度 |
| lng | number | 是 | 经度 |

**响应:**
```json
{
    "success": true,
    "provider": "amap",
    "formatted_address": "北京市东城区天安门广场",
    "province": "北京市",
    "city": "北京市",
    "district": "东城区"
}
```

### GET /api/search-poi

搜索POI。

**查询参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keywords | string | 是 | 搜索关键词 |
| city | string | 否 | 城市 |

**响应:**
```json
{
    "success": true,
    "provider": "amap",
    "pois": [
        {
            "name": "天安门广场",
            "address": "东城区天安门广场",
            "latitude": 39.9042,
            "longitude": 116.4074,
            "type": "风景名胜"
        }
    ]
}
```

---

## 运行时配置

### GET /api/config

读取设置页同步到后端的运行时配置摘要。密钥字段会以 `***` 脱敏返回。

### POST /api/config

保存地图和云存储配置，用于后端地理编码、图片上传和云存储。

**请求体示例:**
```json
{
    "mapProvider": "amap",
    "amapKey": "your-amap-key",
    "storageProvider": "aliyun",
    "aliyunAccessKey": "your-access-key",
    "aliyunSecretKey": "your-secret-key",
    "aliyunBucket": "my-photos",
    "aliyunEndpoint": "oss-cn-hangzhou.aliyuncs.com"
}
```

**响应示例:**
```json
{
    "message": "配置已保存",
    "config": {
        "mapProvider": "amap",
        "amapKey": "***",
        "storageProvider": "aliyun",
        "aliyunAccessKey": "***",
        "aliyunSecretKey": "***",
        "aliyunBucket": "my-photos",
        "aliyunEndpoint": "oss-cn-hangzhou.aliyuncs.com"
    }
}
```

---

## 统计数据

### GET /api/stats

获取统计数据。

**响应:**
```json
{
    "total_records": 42,
    "travel_count": 20,
    "food_count": 15,
    "love_count": 7,
    "total_photos": 156,
    "total_places": 28
}
```

---

## 费用追踪

### GET /api/expenses

获取当前用户的费用列表。

**查询参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| record_id | string | 否 | 按关联记录过滤 |
| page | int | 否 | 页码（从 1 开始） |
| per_page | int | 否 | 每页条数，默认 20，最大 100 |

不传分页参数时返回费用数组；传了 `page` 或 `per_page` 时返回分页结构：

```json
{
    "items": [],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 0,
        "total_pages": 1,
        "has_next": false,
        "has_prev": false
    }
}
```

**费用对象字段:**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 费用 ID |
| record_id | string | 关联记录 ID（可空） |
| mode | string | 模式：travel/food/love，默认 travel |
| category | string | 分类，默认 其他 |
| amount | number | 金额 |
| currency | string | 币种，默认 CNY |
| description | string | 描述 |
| date | string | 日期，格式 YYYY-MM-DD，默认当天 |

### POST /api/expenses

创建费用记录。

**请求体:** 字段同费用对象，`amount` 必填，其余可选

```json
{
    "amount": 128.5,
    "record_id": "abc123",
    "mode": "food",
    "category": "餐饮",
    "currency": "CNY",
    "description": "晚餐",
    "date": "2024-01-15"
}
```

**响应:** `201 Created`，返回创建后的费用对象（含 `id`）

**错误情况:**
- `400`: 缺少 `amount` 或请求体无效

### PUT /api/expenses/<expense_id>

更新费用记录。请求体字段同创建，均可选。

**响应:** `200 OK`，返回更新后的费用对象

**错误情况:**
- `400`: 请求体无效
- `404`: 费用不存在（`{"error": "费用不存在"}`）

### DELETE /api/expenses/<expense_id>

删除费用记录。

**响应:**
```json
{
    "message": "删除成功"
}
```

**错误情况:**
- `404`: 费用不存在

### GET /api/expenses/stats

获取费用统计（按分类与模式汇总金额）。

**响应:**
```json
{
    "total_count": 5,
    "total_amount": 1234.5,
    "by_category": [
        {"category": "餐饮", "count": 3, "amount": 300}
    ],
    "by_mode": [
        {"mode": "travel", "count": 2, "amount": 934.5}
    ]
}
```

---

## 数据导出

所有导出接口均返回文件下载（`Content-Disposition: attachment`），导出内容为当前登录用户自己的记录。导出前请确保已携带 Token。

### GET /api/export/gpx

导出 GPX 1.1 格式轨迹，仅包含有经纬度的记录。

- **响应类型**: `application/gpx+xml`
- **文件名**: `footprint_YYYYMMDD.gpx`

### GET /api/export/geojson

导出 GeoJSON 格式（FeatureCollection，点要素），仅包含有经纬度的记录。

- **响应类型**: `application/geo+json`
- **文件名**: `footprint_YYYYMMDD.geojson`
- **properties 字段**: `id`、`title`、`description`、`location`、`date`、`mode`、`rating`、`image_count`

### GET /api/export/csv

导出 CSV 表格。

- **响应类型**: `text/csv`
- **文件名**: `footprint_YYYYMMDD.csv`
- **列**: `id, mode, title, description, location, latitude, longitude, date, rating, price, image_count, created_at`

---

## 城市统计

### GET /api/cities

从当前用户的记录中提取城市统计（按 `location` 字段中的省/市/区/县/镇前缀归类，按数量降序）。

**响应:**
```json
{
    "cities": [
        {"name": "北京市", "count": 5},
        {"name": "上海市", "count": 2}
    ],
    "total_cities": 2
}
```

---

## AI 故事

### POST /api/ai/story

基于记录生成旅行故事（模板方式，非大模型调用）。

**请求体:**
```json
{
    "record_ids": ["abc123", "def456"],
    "style": "travel"
}
```

- `record_ids`: 可选，指定参与生成的记录 ID 列表；缺省时使用最近 10 条记录
- `style`: 可选，`travel` / `romantic` / `foodie`，默认 `travel`

**响应:**
```json
{
    "story": "🗺️ 这是一段关于 2 个足迹的旅行故事。\n从 2024-01-01 到 2024-01-15，\n足迹遍布 北京市 等地。..."
}
```

**错误情况:**
- `400`: 没有记录

---

## 批量照片上传

### POST /api/upload/batch-photos

批量上传照片并自动提取 EXIF；其中包含 GPS 信息的照片会按平均坐标自动创建一条记录。

**请求:** `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| files | File[] | 是 | 多个图片文件（png/jpg/jpeg/gif/bmp/webp/heic/heif） |
| mode | string | 否 | 生成记录的模式，默认 travel |
| title | string | 否 | 生成记录的标题，默认 批量导入 |

**响应:**
```json
{
    "total": 2,
    "located": 1,
    "record_created": true,
    "record": {
        "id": "abc123",
        "mode": "travel",
        "title": "批量导入",
        "description": "批量导入 2 张照片",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "date": "2024-01-15",
        "images": ["/uploads/abc123.jpg"]
    },
    "files": [
        {
            "url": "/uploads/abc123.jpg",
            "filename": "abc123.jpg"
        }
    ]
}
```

- `total`: 成功保存的文件数
- `located`: 含 GPS 信息的文件数
- `record_created`: 是否自动创建了记录
- `record`: 自动创建的记录（未创建时为 `null`）
- `files`: 每张文件的保存结果（结构同单张上传响应）

**错误情况:**
- `400`: 缺少 `files` 字段

---

## 情侣空间与双人配对

### POST /api/couple/invite
生成一个有效期为 24 小时的 6 位浪漫配对邀请码。

**请求头:** `Authorization: Bearer <token>`

**响应 (200):**
```json
{
    "code": "829104",
    "expires_at": "2026-09-04T12:00:00"
}
```

### POST /api/couple/pair
输入对方生成的 6 位邀请码，建立双人浪漫配对空间。绑定后双方的情侣手账、纪念日、心愿单将自动双向同步。

**请求头:** `Authorization: Bearer <token>`

**请求体:**
```json
{
    "code": "829104"
}
```

**响应 (200):**
```json
{
    "success": true,
    "message": "配对成功！已进入双人专属空间",
    "couple_space_id": "space_9b83f0d2",
    "partner": {
        "id": "user_partner_id",
        "username": "小李"
    }
}
```

### GET /api/couple/status
获取当前登录用户的情侣配对状态。

**请求头:** `Authorization: Bearer <token>`

**响应 (200):**
```json
{
    "paired": true,
    "couple_space_id": "space_9b83f0d2",
    "partner": {
        "id": "user_partner_id",
        "username": "小李"
    }
}
```

### POST /api/couple/unbind
解除当前情侣空间的绑定。

**请求头:** `Authorization: Bearer <token>`

**响应 (200):**
```json
{
    "success": true,
    "message": "已解除双人情侣空间绑定"
}
```

---

## 网页管理后台 (Admin CMS)

### GET /api/admin/overview
获取系统全局健康度、记录数、存储模式与情侣模式状态。

**请求头:** `Authorization: Bearer <token>`

**响应 (200):**
```json
{
    "total_records": 48,
    "total_users": 2,
    "storage_type": "Local (本地持久化存储)",
    "couple_mode": true
}
```

### GET /api/admin/layout
获取前台排版与站点个性化配置。

**响应 (200):**
```json
{
    "siteTitle": "足迹 Footprint",
    "featureOrder": ["map", "replay", "timeline", "globe", "passport", "badges"],
    "heroSubtitle": "探索大千世界，寻味人间烟火"
}
```

### POST /api/admin/layout
保存前台排版与个性化配置。

**请求头:** `Authorization: Bearer <token>`

---

## 错误响应

所有错误响应格式:

```json
{
    "error": "错误描述"
}
```

常见HTTP状态码:
- `200`: 成功
- `201`: 创建成功
- `400`: 请求参数错误
- `401`: 未认证或 Token 无效（见 [认证](#认证authentication)）
- `404`: 资源不存在
- `413`: 请求体超过大小限制（默认 50MB，可用 `MEDIA_MAX_MB` 调整）
- `500`: 服务器内部错误

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| AMAP_KEY | 高德地图API Key | - |
| BAIDU_MAP_KEY | 百度地图API Key | - |
| TENCENT_MAP_KEY | 腾讯地图API Key | - |
| BING_MAP_KEY | 必应地图API Key | - |
| MAP_PROVIDER | 默认地图服务: amap/baidu/tencent/bing | amap |
| DB_TYPE | 数据库类型 | sqlite |
| DB_NAME | 数据库名称 | footprint.db |
| STORAGE_PROVIDER | 存储提供商 | local |
| FLASK_ENV | 运行环境 | production |
| FOOTPRINT_CONFIG_FILE | 设置页运行时配置文件 | backend/runtime_config.json |
| JWT_SECRET_KEY | JWT 签名密钥（生产环境必须设置固定值；未设置时每次启动随机生成，重启后所有 Token 失效） | 随机生成 |
| JWT_EXPIRY_HOURS | Token 有效期（小时） | 24 |
| CORS_ORIGINS | 允许的跨域来源（逗号分隔） | http://localhost:5000,http://127.0.0.1:5000,http://localhost:3000,http://127.0.0.1:3000 |
| MEDIA_MAX_MB | 单次上传大小限制（MB） | 50 |
