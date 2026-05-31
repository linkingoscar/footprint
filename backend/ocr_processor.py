"""
OCR地址识别模块
从图片中识别地址文字
支持百度OCR API和本地OCR
"""

import os
import re
import json

# 百度OCR配置（需要用户自行申请）
BAIDU_APP_ID = os.environ.get('BAIDU_OCR_APP_ID', '')
BAIDU_API_KEY = os.environ.get('BAIDU_OCR_API_KEY', '')
BAIDU_SECRET_KEY = os.environ.get('BAIDU_OCR_SECRET_KEY', '')

def extract_address_from_image(image_path):
    """
    从图片中提取地址信息
    
    返回:
        str: 识别到的地址，或None
    """
    # 优先使用百度OCR
    if BAIDU_API_KEY and BAIDU_SECRET_KEY:
        return _extract_with_baidu_ocr(image_path)
    
    # 备用：简单的本地OCR尝试
    return _extract_with_local_ocr(image_path)

def _extract_with_baidu_ocr(image_path):
    """使用百度OCR识别地址"""
    try:
        from aip import AipOcr
        
        client = AipOcr(BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY)
        
        # 读取图片
        with open(image_path, 'rb') as f:
            image = f.read()
        
        # 调用通用文字识别
        result = client.basicGeneral(image)
        
        if 'words_result' not in result:
            return None
        
        # 提取所有文字
        all_text = ' '.join([item['words'] for item in result['words_result']])
        
        # 使用正则表达式匹配地址
        address = _find_address_in_text(all_text)
        
        return address
        
    except Exception as e:
        print(f"百度OCR错误: {e}")
        return None

def _extract_with_local_ocr(image_path):
    """
    本地OCR（简化版本）
    实际项目中可以集成Tesseract等OCR引擎
    """
    # 这里返回None，表示本地OCR未实现
    # 用户可以集成pytesseract等库
    print("提示：本地OCR未实现，请配置百度OCR API")
    return None

def _find_address_in_text(text):
    """
    从文本中提取地址
    
    地址模式：
    - XX省XX市XX区XX路XX号
    - XX市XX区XX街道
    - 包含省市区路等关键词的文本
    """
    # 地址关键词模式
    patterns = [
        # 完整地址：省市区路号
        r'[\u4e00-\u9fa5]{2,8}(?:省|市|区|县|镇|乡|村)[\u4e00-\u9fa5]{2,20}(?:路|街|道|巷|弄|号|楼|室)',
        # 简单地址：市区+路
        r'[\u4e00-\u9fa5]{2,6}(?:市|区)[\u4e00-\u9fa5]{2,15}(?:路|街|道)',
        # 包含"地址"关键词
        r'(?:地址|地点|位置)[：:]\s*([\u4e00-\u9fa5]{5,50})',
        # 包含"XX路XX号"
        r'[\u4e00-\u9fa5]{2,10}(?:路|街|道|巷)\d{1,5}(?:号|弄)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    # 如果没有匹配到具体地址，返回包含地址关键词的文本片段
    address_keywords = ['省', '市', '区', '县', '路', '街', '道', '号', '楼']
    for keyword in address_keywords:
        if keyword in text:
            # 找到关键词附近的内容
            idx = text.index(keyword)
            start = max(0, idx - 10)
            end = min(len(text), idx + 20)
            return text[start:end].strip()
    
    return None

def ocr_with_custom_config(image_path, config=None):
    """
    使用自定义配置进行OCR
    
    参数:
        image_path: 图片路径
        config: 自定义配置字典
    
    返回:
        dict: OCR结果
    """
    if not BAIDU_API_KEY:
        return {'error': '未配置百度OCR API'}
    
    try:
        from aip import AipOcr
        
        client = AipOcr(BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY)
        
        with open(image_path, 'rb') as f:
            image = f.read()
        
        # 通用文字识别（高精度）
        result = client.basicAccurate(image)
        
        return {
            'words_result': result.get('words_result', []),
            'words_count': result.get('words_result_num', 0)
        }
        
    except Exception as e:
        return {'error': str(e)}
