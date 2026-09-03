"""
足迹 - 数据导出 API 蓝图
"""
import json
import csv
import io
from datetime import datetime
from flask import Blueprint, Response, g

from backend.auth import login_required
from backend.helpers import load_records

export_bp = Blueprint('export', __name__)


@export_bp.route('/api/export/gpx', methods=['GET'])
@login_required
def export_gpx():
    """导出GPX格式轨迹"""
    records = load_records(owner_id=g.current_user['user_id'])
    located = [r for r in records if r.get('latitude') and r.get('longitude')]
    located.sort(key=lambda r: r.get('date', '') or r.get('createdAt', ''))
    
    gpx_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    gpx_parts.append('<gpx version="1.1" creator="足迹 - 记录你的美好生活">')
    gpx_parts.append(f'  <metadata><name>足迹导出</name><time>{datetime.now().isoformat()}</time></metadata>')
    gpx_parts.append('  <trk><name>旅行轨迹</name><trkseg>')
    for r in located:
        date = r.get('date', '')
        title = (r.get('title', '') or '').replace('&', '&amp;').replace('<', '&lt;')
        gpx_parts.append(f'    <trkpt lat="{r["latitude"]}" lon="{r["longitude"]}"><time>{date}</time><name>{title}</name></trkpt>')
    gpx_parts.append('  </trkseg></trk>')
    gpx_parts.append('</gpx>')
    
    content = '\n'.join(gpx_parts)
    return Response(content, mimetype='application/gpx+xml',
                    headers={'Content-Disposition': f'attachment; filename=footprint_{datetime.now().strftime("%Y%m%d")}.gpx'})


@export_bp.route('/api/export/geojson', methods=['GET'])
@login_required
def export_geojson():
    """导出GeoJSON格式"""
    records = load_records(owner_id=g.current_user['user_id'])
    features = []
    for r in records:
        if r.get('latitude') and r.get('longitude'):
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [r['longitude'], r['latitude']]},
                'properties': {
                    'id': r.get('id'),
                    'title': r.get('title', ''),
                    'description': r.get('description', ''),
                    'location': r.get('location', ''),
                    'date': r.get('date', ''),
                    'mode': r.get('mode', ''),
                    'rating': r.get('rating'),
                    'image_count': len(r.get('images', []))
                }
            })
    
    geojson = {'type': 'FeatureCollection', 'features': features}
    content = json.dumps(geojson, ensure_ascii=False, indent=2)
    return Response(content, mimetype='application/geo+json',
                    headers={'Content-Disposition': f'attachment; filename=footprint_{datetime.now().strftime("%Y%m%d")}.geojson'})


@export_bp.route('/api/export/csv', methods=['GET'])
@login_required
def export_csv():
    """导出CSV格式"""
    records = load_records(owner_id=g.current_user['user_id'])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'mode', 'title', 'description', 'location', 'latitude', 'longitude', 'date', 'rating', 'price', 'image_count', 'created_at'])
    for r in records:
        writer.writerow([
            r.get('id', ''),
            r.get('mode', ''),
            r.get('title', ''),
            r.get('description', ''),
            r.get('location', ''),
            r.get('latitude', ''),
            r.get('longitude', ''),
            r.get('date', ''),
            r.get('rating', ''),
            r.get('price', ''),
            len(r.get('images', [])),
            r.get('createdAt', '')
        ])
    
    content = output.getvalue()
    return Response(content, mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=footprint_{datetime.now().strftime("%Y%m%d")}.csv'})


@export_bp.route('/api/export/json', methods=['GET'])
@login_required
def export_json():
    """导出完整 JSON 备份文件，携带标准 schemaVersion 与导出元数据"""
    records = load_records(owner_id=g.current_user['user_id'])
    payload = {
        'schemaVersion': 1,
        'app': 'Footprint',
        'exportedAt': datetime.now().isoformat(),
        'count': len(records),
        'records': records
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(content, mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename=footprint_backup_{datetime.now().strftime("%Y%m%d")}.json'})
