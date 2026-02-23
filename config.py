"""博客系统配置文件"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'myblob-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'blog.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 博客配置
    BLOG_TITLE = 'mengfei博客'
    BLOG_SUBTITLE = '记录工作和生活的点滴'
    POSTS_PER_PAGE = 10

    # Markdown 文件目录
    MARKDOWN_FOLDER = os.path.join(basedir, 'posts')

    # GitHub 代理配置
    GITHUB_PROXY_ENABLED = True
    GITHUB_RAW_BASE = 'https://raw.githubusercontent.com'
    GITHUB_API_BASE = 'https://api.github.com'

    # 允许的主题列表
    THEMES = ['light', 'dark', 'ocean', 'forest', 'sunset']
    DEFAULT_THEME = 'light'


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
