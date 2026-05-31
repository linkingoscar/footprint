"""
EXIF GPS信息提取模块
从图片中提取GPS坐标信息
"""

import exifread
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime

def convert_to_degrees(value):
    """将EXIF GPS坐标转换为十进制度数"""
    try:
        # exifread返回的IfdTag对象
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None

def extract_gps_from_image(image_path):
    """
    从图片中提取GPS信息
    
    返回:
        dict: {'latitude': float, 'longitude': float} 或 None
    """
    try:
        # 方法1: 使用exifread（更可靠）
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        
        # 检查是否有GPS信息
        gps_lat = tags.get('GPS GPSLatitude')
        gps_lat_ref = tags.get('GPS GPSLatitudeRef')
        gps_lon = tags.get('GPS GPSLongitude')
        gps_lon_ref = tags.get('GPS GPSLongitudeRef')
        
        if gps_lat and gps_lon and gps_lat_ref and gps_lon_ref:
            latitude = convert_to_degrees(gps_lat)
            longitude = convert_to_degrees(gps_lon)
            
            if latitude is None or longitude is None:
                return None
            
            # 南纬和西经为负数
            if gps_lat_ref.values == 'S':
                latitude = -latitude
            if gps_lon_ref.values == 'W':
                longitude = -longitude
            
            # 验证坐标范围
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                return {
                    'latitude': round(latitude, 6),
                    'longitude': round(longitude, 6)
                }
        
        # 方法2: 使用Pillow作为备用
        return _extract_with_pillow(image_path)
        
    except Exception as e:
        print(f"EXIF提取错误: {e}")
        return None

def _extract_with_pillow(image_path):
    """使用Pillow提取GPS信息（备用方法）"""
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        
        if not exif_data:
            return None
        
        # 查找GPS信息
        gps_info = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'GPSInfo':
                for gps_tag_id, gps_value in value.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag] = gps_value
        
        if 'GPSLatitude' not in gps_info or 'GPSLongitude' not in gps_info:
            return None
        
        # 转换坐标
        lat = gps_info['GPSLatitude']
        lon = gps_info['GPSLongitude']
        lat_ref = gps_info.get('GPSLatitudeRef', 'N')
        lon_ref = gps_info.get('GPSLongitudeRef', 'E')
        
        latitude = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / 3600
        longitude = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / 3600
        
        if lat_ref == 'S':
            latitude = -latitude
        if lon_ref == 'W':
            longitude = -longitude
        
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            return {
                'latitude': round(latitude, 6),
                'longitude': round(longitude, 6)
            }
        
        return None
        
    except Exception as e:
        print(f"Pillow EXIF提取错误: {e}")
        return None

def get_image_info(image_path):
    """获取图片基本信息"""
    try:
        image = Image.open(image_path)
        return {
            'width': image.width,
            'height': image.height,
            'format': image.format,
            'mode': image.mode
        }
    except Exception as e:
        print(f"获取图片信息错误: {e}")
        return None

def extract_datetime_from_image(image_path):
    """提取图片拍摄时间，返回 YYYY-MM-DD 格式。"""
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data:
            return None

        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime'):
                try:
                    return datetime.strptime(str(value), '%Y:%m:%d %H:%M:%S').strftime('%Y-%m-%d')
                except ValueError:
                    continue
        return None
    except Exception as e:
        print(f"提取拍摄时间错误: {e}")
        return None
