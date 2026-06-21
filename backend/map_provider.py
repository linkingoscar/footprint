"""
足迹 - 地图服务策略模式
支持高德、百度、腾讯、必应四种地图服务的统一接口。
"""

import requests
from abc import ABC, abstractmethod


class MapProvider(ABC):
    """地图服务抽象基类"""

    @abstractmethod
    def geocode(self, address: str, key: str) -> dict:
        """地址 → 坐标"""
        pass

    @abstractmethod
    def reverse_geocode(self, lat: float, lng: float, key: str) -> dict:
        """坐标 → 地址"""
        pass

    @abstractmethod
    def search_poi(self, keywords: str, city: str, key: str) -> dict:
        """搜索POI兴趣点"""
        pass


class AmapProvider(MapProvider):
    """高德地图"""

    def geocode(self, address: str, key: str) -> dict:
        try:
            url = 'https://restapi.amap.com/v3/geocode/geo'
            params = {
                'key': key,
                'address': address,
                'output': 'JSON'
            }
            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            if data['status'] == '1' and data['geocodes']:
                geocode = data['geocodes'][0]
                location = geocode['location'].split(',')
                return {
                    'success': True,
                    'provider': 'amap',
                    'latitude': float(location[1]),
                    'longitude': float(location[0]),
                    'formatted_address': geocode['formatted_address'],
                    'province': geocode.get('province', ''),
                    'city': geocode.get('city', ''),
                    'district': geocode.get('district', '')
                }
            return {'success': False, 'provider': 'amap', 'error': '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}

    def reverse_geocode(self, lat: float, lng: float, key: str) -> dict:
        try:
            url = 'https://restapi.amap.com/v3/geocode/regeo'
            params = {
                'key': key,
                'location': f'{lng},{lat}',
                'output': 'JSON'
            }
            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            if data['status'] == '1':
                regeocode = data['regeocode']
                return {
                    'success': True,
                    'provider': 'amap',
                    'formatted_address': regeocode['formatted_address'],
                    'province': regeocode['addressComponent'].get('province', ''),
                    'city': regeocode['addressComponent'].get('city', ''),
                    'district': regeocode['addressComponent'].get('district', '')
                }
            return {'success': False, 'provider': 'amap', 'error': '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}

    def search_poi(self, keywords: str, city: str, key: str) -> dict:
        try:
            url = 'https://restapi.amap.com/v3/place/text'
            params = {
                'key': key,
                'keywords': keywords,
                'city': city,
                'output': 'JSON',
                'offset': 10
            }
            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            if data['status'] == '1':
                pois = []
                for poi in data.get('pois', []):
                    location = poi['location'].split(',')
                    pois.append({
                        'name': poi['name'],
                        'address': poi.get('address', ''),
                        'latitude': float(location[1]),
                        'longitude': float(location[0]),
                        'type': poi.get('type', '')
                    })
                return {'success': True, 'provider': 'amap', 'pois': pois}
            return {'success': False, 'provider': 'amap', 'error': '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}


class BaiduProvider(MapProvider):
    """百度地图"""

    def geocode(self, address: str, key: str) -> dict:
        try:
            response = requests.get('https://api.map.baidu.com/geocoding/v3/', params={
                'ak': key,
                'address': address,
                'output': 'json'
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0 and data.get('result'):
                result = data['result']
                location = result['location']
                return {
                    'success': True,
                    'provider': 'baidu',
                    'latitude': float(location['lat']),
                    'longitude': float(location['lng']),
                    'formatted_address': result.get('formatted_address') or address,
                    'province': '',
                    'city': '',
                    'district': ''
                }
            return {'success': False, 'provider': 'baidu', 'error': data.get('message') or '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}

    def reverse_geocode(self, lat: float, lng: float, key: str) -> dict:
        try:
            response = requests.get('https://api.map.baidu.com/reverse_geocoding/v3/', params={
                'ak': key,
                'location': f'{lat},{lng}',
                'output': 'json'
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0 and data.get('result'):
                result = data['result']
                components = result.get('addressComponent', {})
                return {
                    'success': True,
                    'provider': 'baidu',
                    'formatted_address': result.get('formatted_address', ''),
                    'province': components.get('province', ''),
                    'city': components.get('city', ''),
                    'district': components.get('district', '')
                }
            return {'success': False, 'provider': 'baidu', 'error': data.get('message') or '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}

    def search_poi(self, keywords: str, city: str, key: str) -> dict:
        try:
            response = requests.get('https://api.map.baidu.com/place/v2/search', params={
                'ak': key,
                'query': keywords,
                'region': city or '全国',
                'output': 'json',
                'page_size': 10
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0:
                pois = []
                for poi in data.get('results', []):
                    location = poi.get('location') or {}
                    if 'lat' not in location or 'lng' not in location:
                        continue
                    pois.append({
                        'name': poi.get('name', ''),
                        'address': poi.get('address', ''),
                        'latitude': float(location['lat']),
                        'longitude': float(location['lng']),
                        'type': poi.get('tag', '')
                    })
                return {'success': True, 'provider': 'baidu', 'pois': pois}
            return {'success': False, 'provider': 'baidu', 'error': data.get('message') or '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}


class TencentProvider(MapProvider):
    """腾讯地图"""

    def geocode(self, address: str, key: str) -> dict:
        try:
            response = requests.get('https://apis.map.qq.com/ws/geocoder/v1/', params={
                'key': key,
                'address': address
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0 and data.get('result'):
                result = data['result']
                location = result['location']
                components = result.get('address_components', {})
                return {
                    'success': True,
                    'provider': 'tencent',
                    'latitude': float(location['lat']),
                    'longitude': float(location['lng']),
                    'formatted_address': result.get('title') or address,
                    'province': components.get('province', ''),
                    'city': components.get('city', ''),
                    'district': components.get('district', '')
                }
            return {'success': False, 'provider': 'tencent', 'error': data.get('message') or '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}

    def reverse_geocode(self, lat: float, lng: float, key: str) -> dict:
        try:
            response = requests.get('https://apis.map.qq.com/ws/geocoder/v1/', params={
                'key': key,
                'location': f'{lat},{lng}'
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0 and data.get('result'):
                result = data['result']
                components = result.get('address_component', {})
                return {
                    'success': True,
                    'provider': 'tencent',
                    'formatted_address': result.get('address', ''),
                    'province': components.get('province', ''),
                    'city': components.get('city', ''),
                    'district': components.get('district', '')
                }
            return {'success': False, 'provider': 'tencent', 'error': data.get('message') or '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}

    def search_poi(self, keywords: str, city: str, key: str) -> dict:
        try:
            response = requests.get('https://apis.map.qq.com/ws/place/v1/search', params={
                'key': key,
                'keyword': keywords,
                'boundary': f"region({city or '全国'},0)",
                'page_size': 10
            }, timeout=5)
            data = response.json()
            if data.get('status') == 0:
                pois = []
                for poi in data.get('data', []):
                    location = poi.get('location') or {}
                    if 'lat' not in location or 'lng' not in location:
                        continue
                    pois.append({
                        'name': poi.get('title', ''),
                        'address': poi.get('address', ''),
                        'latitude': float(location['lat']),
                        'longitude': float(location['lng']),
                        'type': poi.get('category', '')
                    })
                return {'success': True, 'provider': 'tencent', 'pois': pois}
            return {'success': False, 'provider': 'tencent', 'error': data.get('message') or '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}


class BingProvider(MapProvider):
    """必应地图"""

    def geocode(self, address: str, key: str) -> dict:
        try:
            response = requests.get('https://dev.virtualearth.net/REST/v1/Locations', params={
                'key': key,
                'q': address,
                'maxResults': 1
            }, timeout=5)
            data = response.json()
            resources = data.get('resourceSets', [{}])[0].get('resources', [])
            if resources:
                result = resources[0]
                lat, lng = result['point']['coordinates']
                addr = result.get('address', {})
                return {
                    'success': True,
                    'provider': 'bing',
                    'latitude': float(lat),
                    'longitude': float(lng),
                    'formatted_address': addr.get('formattedAddress') or result.get('name') or address,
                    'province': addr.get('adminDistrict', ''),
                    'city': addr.get('locality', ''),
                    'district': addr.get('adminDistrict2', '')
                }
            return {'success': False, 'provider': 'bing', 'error': '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}

    def reverse_geocode(self, lat: float, lng: float, key: str) -> dict:
        try:
            response = requests.get(f'https://dev.virtualearth.net/REST/v1/Locations/{lat},{lng}', params={
                'key': key,
                'maxResults': 1
            }, timeout=5)
            data = response.json()
            resources = data.get('resourceSets', [{}])[0].get('resources', [])
            if resources:
                addr = resources[0].get('address', {})
                return {
                    'success': True,
                    'provider': 'bing',
                    'formatted_address': addr.get('formattedAddress', ''),
                    'province': addr.get('adminDistrict', ''),
                    'city': addr.get('locality', ''),
                    'district': addr.get('adminDistrict2', '')
                }
            return {'success': False, 'provider': 'bing', 'error': '未找到结果'}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}

    def search_poi(self, keywords: str, city: str, key: str) -> dict:
        try:
            response = requests.get('https://dev.virtualearth.net/REST/v1/Locations', params={
                'key': key,
                'q': keywords,
                'maxResults': 10
            }, timeout=5)
            data = response.json()
            pois = []
            for item in data.get('resourceSets', [{}])[0].get('resources', []):
                coordinates = item.get('point', {}).get('coordinates')
                if not coordinates or len(coordinates) < 2:
                    continue
                addr = item.get('address', {})
                pois.append({
                    'name': item.get('name', ''),
                    'address': addr.get('formattedAddress', ''),
                    'latitude': float(coordinates[0]),
                    'longitude': float(coordinates[1]),
                    'type': item.get('entityType', '')
                })
            return {'success': True, 'provider': 'bing', 'pois': pois}
        except Exception:
            return {'success': False, 'error': '服务内部错误'}


# Provider registry
PROVIDERS = {
    'amap': AmapProvider(),
    'baidu': BaiduProvider(),
    'tencent': TencentProvider(),
    'bing': BingProvider(),
}


def get_provider(name: str) -> MapProvider:
    """获取地图服务提供商实例"""
    return PROVIDERS.get(name, PROVIDERS['amap'])
