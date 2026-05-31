# 足迹 API 文档

## 基础信息

- **Base URL**: `http://localhost:5000/api`
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

## 目录

- [健康检查](#健康检查)
- [记录管理](#记录管理)
- [图片上传](#图片上传)
- [地理编码](#地理编码)
- [运行时配置](#运行时配置)
- [统计数据](#统计数据)

---

## 健康检查

### GET /api/health

检查服务是否正常运行。

**响应示例:**
```json
{
    "status": "ok",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "amap_configured": true,
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
- `404`: 资源不存在
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
