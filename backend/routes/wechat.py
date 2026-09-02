"""
足迹 - 微信小程序对接 API 蓝图
提供小程序原生认证、code2session 转换、沙盒体验与配置检测。
"""
import urllib.request
import urllib.parse
import json
from flask import Blueprint, request, jsonify

from backend.auth import generate_token, get_current_user
from backend.helpers import get_record_store, get_runtime_config

wechat_bp = Blueprint('wechat', __name__)


@wechat_bp.route('/api/wechat/config', methods=['GET'])
def wechat_config():
    """获取小程序端公开配置状态"""
    config = get_runtime_config()
    app_id = config.get('wechatAppId')
    app_secret = config.get('wechatAppSecret')
    mock_login = config.get('wechatMockLogin', True)  # 默认在无 Key 时允许沙盒体验

    return jsonify({
        'success': True,
        'has_app_id': bool(app_id),
        'configured': bool(app_id and app_secret),
        'mock_enabled': bool(mock_login)
    })


@wechat_bp.route('/api/wechat/login', methods=['POST'])
def wechat_login():
    """
    微信小程序登录凭证校验 (code2session)
    客户端 wx.login() 得到 code，发送给本接口兑换 JWT Token
    """
    data = request.get_json() or {}
    code = data.get('code', '').strip()

    config = get_runtime_config()
    app_id = config.get('wechatAppId')
    app_secret = config.get('wechatAppSecret')
    mock_login = config.get('wechatMockLogin', True)

    store = get_record_store()

    # 1. 生产模式：已配置 AppID 和 AppSecret
    if app_id and app_secret and code and code != 'mock_code':
        wx_url = (
            f"https://api.weixin.qq.com/sns/jscode2session?"
            f"appid={urllib.parse.quote(app_id)}&"
            f"secret={urllib.parse.quote(app_secret)}&"
            f"js_code={urllib.parse.quote(code)}&"
            f"grant_type=authorization_code"
        )
        try:
            req = urllib.request.Request(wx_url, headers={'User-Agent': 'Footprint-WeChat/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            
            errcode = result.get('errcode', 0)
            if errcode != 0:
                errmsg = result.get('errmsg', '微信接口认证错误')
                return jsonify({'error': f'微信登录失败: {errmsg}', 'errcode': errcode}), 400

            openid = result.get('openid')
            if not openid:
                return jsonify({'error': '未获取到微信 OpenID'}), 400

            # 绑定或创建微信用户
            username = f"wx_{openid[:10]}"
            user = None
            if hasattr(store, 'get_user_by_username'):
                user = store.get_user_by_username(username)
            if not user and hasattr(store, 'create_user'):
                user = store.create_user(username, openid)  # 使用 openid 派生密码

            user_dict = user if user else {'id': f'user_{openid[:12]}', 'username': username}
            token = generate_token(user_dict['id'], user_dict['username'])
            return jsonify({
                'success': True,
                'token': token,
                'user': user_dict,
                'openid': openid
            })
        except Exception as e:
            # 微信网络超时或失败时，若允许 mock 则回退到沙盒，否则报错
            if not mock_login:
                return jsonify({'error': f'连接微信服务器失败: {str(e)}'}), 502

    # 2. 沙盒或本地测试模式：无 AppID/Secret 或指定了 mock
    if mock_login:
        mock_id = 'user_wechat_sandbox'
        mock_username = '微信体验用户'
        mock_user = {'id': mock_id, 'username': mock_username, 'role': 'user'}
        token = generate_token(mock_id, mock_username)
        return jsonify({
            'success': True,
            'token': token,
            'user': mock_user,
            'mock': True,
            'message': '微信沙盒模式登录成功 (未配置 AppID/Secret 时的无缝调试通道)'
        })

    return jsonify({'error': '未配置小程序 AppID/Secret 且沙盒登录已关闭'}), 400
