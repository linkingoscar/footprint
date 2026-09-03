"""
足迹 - 地理编码 API 蓝图
使用 MapProvider 策略模式替代 if-elif 链。
"""
from flask import Blueprint, request, jsonify

from backend.auth import login_required
from backend.helpers import get_map_provider, get_map_key, map_key_configured
from backend.map_provider import get_provider

geocode_bp = Blueprint('geocode', __name__)


@geocode_bp.route('/api/geocode', methods=['GET'])
@login_required
def geocode():
    """地理编码：地址 -> 坐标"""
    address = request.args.get('address')
    if not address:
        return jsonify({'error': '缺少地址参数'}), 400

    provider_name = get_map_provider()
    key = get_map_key(provider_name)
    if not map_key_configured(provider_name):
        return jsonify({'success': False, 'error': f'{provider_name} 地图 API Key 未配置'}), 400

    provider = get_provider(provider_name)
    result = provider.geocode(address, key)
    return jsonify(result)


@geocode_bp.route('/api/reverse-geocode', methods=['GET'])
@geocode_bp.route('/api/geocode/reverse', methods=['GET'])
@login_required
def reverse_geocode():
    """逆地理编码：坐标 -> 地址"""
    lat = request.args.get('lat')
    lng = request.args.get('lng')

    if not lat or not lng:
        return jsonify({'error': '缺少坐标参数'}), 400

    provider_name = get_map_provider()
    key = get_map_key(provider_name)
    if not map_key_configured(provider_name):
        return jsonify({'success': False, 'error': f'{provider_name} 地图 API Key 未配置'}), 400

    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return jsonify({'error': '坐标参数格式错误'}), 400

    provider = get_provider(provider_name)
    result = provider.reverse_geocode(lat_f, lng_f, key)
    return jsonify(result)


@geocode_bp.route('/api/search-poi', methods=['GET'])
@login_required
def search_poi():
    """搜索POI兴趣点"""
    keywords = request.args.get('keywords')
    city = request.args.get('city', '')

    if not keywords:
        return jsonify({'error': '缺少搜索关键词'}), 400

    provider_name = get_map_provider()
    key = get_map_key(provider_name)
    if not map_key_configured(provider_name):
        return jsonify({'success': False, 'error': f'{provider_name} 地图 API Key 未配置'}), 400

    provider = get_provider(provider_name)
    result = provider.search_poi(keywords, city, key)
    return jsonify(result)
