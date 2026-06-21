"""
足迹 - 路由蓝图注册
"""
from flask import Flask

def register_blueprints(app: Flask):
    """注册所有路由蓝图"""
    from .auth import auth_bp
    from .records import records_bp
    from .upload import upload_bp
    from .config import config_bp
    from .geocode import geocode_bp
    from .export import export_bp
    from .expenses import expenses_bp
    from .misc import misc_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(geocode_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(misc_bp)
