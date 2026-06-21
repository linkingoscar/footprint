"""
足迹 - 杂项 API 蓝图
统计、健康检查、城市统计、AI故事生成、批量照片导入
"""
import uuid
import os
from datetime import datetime
from flask import Blueprint, request, jsonify

from backend.helpers import (
    get_record_store, load_records, get_storage_provider,
    get_map_provider, map_key_configured, allowed_file,
    save_upload_file, normalize_record_payload, DB_TYPE
)

misc_bp = Blueprint('misc', __name__)


@misc_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    records = load_records()
    
    monthly = {}
    places = sorted(set(r.get('location') for r in records if r.get('location')))
    for record in records:
        date = record.get('date') or record.get('createdAt', '')[:10]
        if date:
            month = date[:7]
            monthly[month] = monthly.get(month, 0) + 1

    return jsonify({
        'total_records': len(records),
        'travel_count': len([r for r in records if r.get('mode') == 'travel']),
        'food_count': len([r for r in records if r.get('mode') == 'food']),
        'love_count': len([r for r in records if r.get('mode') == 'love']),
        'total_photos': sum(len(r.get('images', [])) for r in records),
        'total_places': len(places),
        'places': places,
        'monthly_trend': monthly,
        'storage_provider': get_storage_provider()
    })


@misc_bp.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'map_provider': get_map_provider(),
        'map_configured': map_key_configured(),
        'storage_provider': get_storage_provider(),
        'db_type': os.environ.get('DB_TYPE', DB_TYPE)
    })


@misc_bp.route('/api/cities', methods=['GET'])
def get_cities():
    """从记录中提取城市统计"""
    records = load_records()
    cities = {}
    for r in records:
        loc = r.get('location', '')
        if not loc:
            continue
        # 简单提取城市名
        city = loc
        for sep in ['省', '市', '区', '县', '镇']:
            idx = loc.find(sep)
            if idx > 0:
                city = loc[:idx + len(sep)]
                break
        if city:
            cities[city] = cities.get(city, 0) + 1
    
    return jsonify({
        'cities': [{'name': k, 'count': v} for k, v in sorted(cities.items(), key=lambda x: -x[1])],
        'total_cities': len(cities)
    })


@misc_bp.route('/api/ai/story', methods=['POST'])
def generate_story():
    """基于记录生成旅行故事（模板方式）"""
    data = request.get_json() or {}
    record_ids = data.get('record_ids', [])
    style = data.get('style', 'travel')
    
    store = get_record_store()
    if record_ids:
        records = [store.get(rid) for rid in record_ids if store.get(rid)]
    else:
        records = load_records()[:10]
    
    if not records:
        return jsonify({'error': '没有记录'}), 400
    
    story_parts = []
    places = [r.get('location', '') for r in records if r.get('location')]
    dates = [r.get('date', '') for r in records if r.get('date')]
    
    if style == 'travel':
        story_parts.append(f'🗺️ 这是一段关于 {len(records)} 个足迹的旅行故事。')
        if dates:
            story_parts.append(f'从 {min(dates)} 到 {max(dates)}，')
        if places:
            story_parts.append(f'足迹遍布 {"、".join(places[:5])} 等地。\n')
        for r in records[:8]:
            if r.get('title'):
                loc = r.get('location', '这里')
                desc = r.get('description', '') or '留下了美好的回忆'
                story_parts.append(f'📍 {r.get("date", "")} · {loc}')
                story_parts.append(f'   {r.get("title")} — {desc}\n')
    elif style == 'romantic':
        story_parts.append(f'💕 这是一段 {len(records)} 个甜蜜瞬间的爱情故事。\n')
        for r in records[:8]:
            if r.get('title'):
                story_parts.append(f'📅 {r.get("date", "")} · {r.get("location", "")}')
                story_parts.append(f'   {r.get("description", r.get("title"))}\n')
    elif style == 'foodie':
        story_parts.append(f'🍜 {len(records)} 道美食的味蕾之旅。\n')
        for r in records[:8]:
            if r.get('title'):
                rating = '⭐' * (r.get('rating', 0) or 0)
                price = f'¥{r.get("price", "")}' if r.get('price') else ''
                story_parts.append(f'🍽️ {r.get("title")} {rating} {price}')
                story_parts.append(f'   {r.get("description", "")}\n')
    
    return jsonify({'story': '\n'.join(story_parts)})


@misc_bp.route('/api/upload/batch-photos', methods=['POST'])
def upload_batch_photos():
    """批量上传照片并自动提取EXIF"""
    if 'files' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    files = request.files.getlist('files')
    mode = request.form.get('mode', 'travel')
    title = request.form.get('title', '批量导入')
    
    results = []
    for file in files:
        if file.filename == '' or not allowed_file(file.filename):
            continue
        result, error = save_upload_file(file)
        if not error:
            results.append(result)
    
    # 有GPS数据的自动创建记录
    located = [r for r in results if r.get('latitude')]
    record = None
    if located:
        record = {
            'id': uuid.uuid4().hex,
            'mode': mode,
            'title': title,
            'description': f'批量导入 {len(results)} 张照片',
            'latitude': sum(r['latitude'] for r in located) / len(located),
            'longitude': sum(r['longitude'] for r in located) / len(located),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'images': [r['url'] for r in results],
            'tags': [],
            'metadata': {'images': results}
        }
        get_record_store().create(record)
    
    return jsonify({
        'total': len(results),
        'located': len(located),
        'record_created': record is not None,
        'record': record,
        'files': results
    })
