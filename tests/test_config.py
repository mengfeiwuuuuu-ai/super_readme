"""配置文件单元测试"""
import os
import pytest
from config import Config, DevelopmentConfig, ProductionConfig, config


class TestConfig:
    """基础配置测试"""

    def test_secret_key_exists(self):
        """测试 SECRET_KEY 存在"""
        assert Config.SECRET_KEY is not None
        assert len(Config.SECRET_KEY) > 0

    def test_database_uri(self):
        """测试数据库 URI 配置"""
        assert Config.SQLALCHEMY_DATABASE_URI is not None
        assert 'sqlite' in Config.SQLALCHEMY_DATABASE_URI

    def test_track_modifications_disabled(self):
        """测试 SQLALCHEMY_TRACK_MODIFICATIONS 已禁用"""
        assert Config.SQLALCHEMY_TRACK_MODIFICATIONS is False

    def test_blog_title(self):
        """测试博客标题配置"""
        assert Config.BLOG_TITLE is not None
        assert len(Config.BLOG_TITLE) > 0

    def test_posts_per_page(self):
        """测试每页文章数"""
        assert Config.POSTS_PER_PAGE > 0

    def test_markdown_folder(self):
        """测试 Markdown 文件夹配置"""
        assert Config.MARKDOWN_FOLDER is not None

    def test_themes_list(self):
        """测试主题列表"""
        assert isinstance(Config.THEMES, list)
        assert len(Config.THEMES) > 0
        assert 'light' in Config.THEMES
        assert 'dark' in Config.THEMES

    def test_default_theme(self):
        """测试默认主题"""
        assert Config.DEFAULT_THEME in Config.THEMES

    def test_github_proxy_config(self):
        """测试 GitHub 代理配置"""
        assert Config.GITHUB_PROXY_ENABLED is True
        assert 'github.com' in Config.GITHUB_API_BASE
        assert 'githubusercontent.com' in Config.GITHUB_RAW_BASE


class TestDevelopmentConfig:
    """开发环境配置测试"""

    def test_debug_enabled(self):
        """测试开发环境 DEBUG 开启"""
        assert DevelopmentConfig.DEBUG is True

    def test_inherits_base_config(self):
        """测试继承基础配置"""
        assert hasattr(DevelopmentConfig, 'SECRET_KEY')
        assert hasattr(DevelopmentConfig, 'SQLALCHEMY_DATABASE_URI')


class TestProductionConfig:
    """生产环境配置测试"""

    def test_debug_disabled(self):
        """测试生产环境 DEBUG 关闭"""
        assert ProductionConfig.DEBUG is False


class TestConfigMapping:
    """配置映射测试"""

    def test_config_dict_exists(self):
        """测试配置字典存在"""
        assert 'development' in config
        assert 'production' in config
        assert 'default' in config

    def test_default_is_development(self):
        """测试默认配置为开发环境"""
        assert config['default'] is DevelopmentConfig
