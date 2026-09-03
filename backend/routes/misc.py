"""
足迹 - 杂项 API 蓝图
统计、健康检查、城市统计、AI故事生成、批量照片导入
"""
import uuid
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from backend.auth import login_required
from backend.helpers import (
    get_record_store, load_records, get_storage_provider,
    get_map_provider, map_key_configured, allowed_file,
    save_upload_file, normalize_record_payload, DB_TYPE,
    get_runtime_config
)

misc_bp = Blueprint('misc', __name__)


@misc_bp.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """获取统计数据"""
    owner_id = g.current_user['user_id']
    records = load_records(owner_id=owner_id)
    
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
    """健康检查接口（无需认证，供容器探针使用）"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'map_provider': get_map_provider(),
        'map_configured': map_key_configured(),
        'storage_provider': get_storage_provider(),
        'db_type': os.environ.get('DB_TYPE', DB_TYPE)
    })


@misc_bp.route('/api/cities', methods=['GET'])
@login_required
def get_cities():
    """从记录中提取城市统计"""
    records = load_records(owner_id=g.current_user['user_id'])
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


def _generate_template_story(records, style):
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
    
    return '\n'.join(story_parts)


def _generate_llm_story(records, style, api_key, api_base, model):
    import requests
    base_url = (api_base or 'https://api.openai.com/v1').rstrip('/')
    url = f"{base_url}/chat/completions"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    summary_items = []
    for r in records[:15]:
        item_str = f"时间: {r.get('date', '未知')}, 地点: {r.get('location', '未知')}, 标题: {r.get('title', '')}"
        if r.get('description'):
            item_str += f", 描述: {r.get('description')}"
        if r.get('rating'):
            item_str += f", 评分: {r.get('rating')}星"
        if r.get('price'):
            item_str += f", 价格: ¥{r.get('price')}"
        summary_items.append(item_str)
    
    context = "\n".join(summary_items)
    
    style_prompts = {
        'travel': "请以游记作家细腻生动的笔触，根据以下旅行足迹创作一篇富有画面感、文学色彩与人文温度的游记散文。篇幅约300-500字，适度使用emoji点缀。",
        'romantic': "请以深情、浪漫、温馨的笔触，根据以下情侣足迹创作一段记录两人美好回忆的恋爱纪念故事。篇幅约300-500字，适度使用💕等emoji。",
        'foodie': "请以资深老饕与美食专栏作者的视角，根据以下美食记录创作一篇色香味俱全的美食鉴赏日志。篇幅约300-500字，适度使用🍜🍽️等emoji。"
    }
    instruction = style_prompts.get(style, style_prompts['travel'])
    
    messages = [
        {"role": "system", "content": "你是一位富有才华的旅行生活记录作家，善于把生活足迹串联成真挚优美的故事。"},
        {"role": "user", "content": f"{instruction}\n\n记录清单：\n{context}"}
    ]
    
    resp = requests.post(url, headers=headers, json={
        "model": model or "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000
    }, timeout=20)
    
    if resp.status_code == 200:
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    return None


@misc_bp.route('/api/ai/story', methods=['POST'])
@login_required
def generate_story():
    """基于记录生成旅行故事（支持真实 LLM 创作与内置模板平滑降级）"""
    data = request.get_json(silent=True) or {}
    record_ids = data.get('record_ids', [])
    style = data.get('style', 'travel')
    
    store = get_record_store()
    owner_id = g.current_user['user_id']
    if record_ids:
        records = [store.get(rid, owner_id) for rid in record_ids]
        records = [r for r in records if r]
    else:
        records = load_records(owner_id=owner_id)[:10]
    
    if not records:
        return jsonify({'error': '没有记录'}), 400

    runtime_config = get_runtime_config()
    api_key = (
        data.get('api_key') or
        runtime_config.get('aiApiKey') or
        os.environ.get('AI_API_KEY') or
        os.environ.get('OPENAI_API_KEY')
    )
    api_base = (
        data.get('api_base') or
        runtime_config.get('aiApiBase') or
        os.environ.get('AI_API_BASE') or
        os.environ.get('OPENAI_BASE_URL') or
        os.environ.get('OPENAI_API_BASE') or
        'https://api.openai.com/v1'
    )
    model = (
        data.get('model') or
        runtime_config.get('aiModel') or
        os.environ.get('AI_MODEL') or
        os.environ.get('OPENAI_MODEL') or
        'deepseek-chat'
    )

    story = None
    is_llm = False
    if api_key:
        try:
            story = _generate_llm_story(records, style, api_key, api_base, model)
            if story:
                is_llm = True
        except Exception:
            story = None

    if not story:
        story = _generate_template_story(records, style)

    return jsonify({
        'story': story,
        'mode': 'ai' if is_llm else 'template',
        'has_ai_key': bool(api_key)
    })


@misc_bp.route('/api/upload/batch-photos', methods=['POST'])
@login_required
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
        get_record_store().create(record, g.current_user['user_id'])
    
    return jsonify({
        'total': len(results),
        'located': len(located),
        'record_created': record is not None,
        'record': record,
        'files': results
    })
