"""测试共享 Fixtures"""
import os
import sys
import shutil
import tempfile

import pytest

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, init_db
from models import db as _db, User, Post, Category


# ==================== 测试配置 ====================

class TestConfig:
    """测试专用配置"""
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost'
    BLOG_TITLE = '测试博客'
    BLOG_SUBTITLE = '单元测试'
    POSTS_PER_PAGE = 5
    MARKDOWN_FOLDER = ''  # 会在 fixture 中动态设置
    GITHUB_PROXY_ENABLED = True
    GITHUB_RAW_BASE = 'https://raw.githubusercontent.com'
    GITHUB_API_BASE = 'https://api.github.com'
    THEMES = ['light', 'dark', 'ocean', 'forest', 'sunset']
    DEFAULT_THEME = 'light'
    LOGIN_DISABLED = False


# ==================== 应用和数据库 Fixtures ====================

@pytest.fixture(scope='function')
def app(tmp_path):
    """创建测试应用实例"""
    posts_dir = tmp_path / 'posts'
    posts_dir.mkdir()

    TestConfig.MARKDOWN_FOLDER = str(posts_dir)

    test_app = create_app.__wrapped__(TestConfig) if hasattr(create_app, '__wrapped__') else None
    if test_app is None:
        # 手动创建 app，因为 create_app 接受 config_name 字符串
        from flask import Flask
        from flask_login import LoginManager
        import markdown as md_lib
        from markupsafe import Markup
        from models import db as db_ext
        from utils.github_proxy import GitHubProxy
        from utils.markdown_scanner import scan_markdown_folder, generate_slug, generate_summary
        from datetime import datetime
        from functools import wraps

        test_app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
                         static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))
        test_app.config.from_object(TestConfig)

        db_ext.init_app(test_app)

        login_manager = LoginManager()
        login_manager.init_app(test_app)
        login_manager.login_view = 'login'
        login_manager.login_message = '请先登录'
        login_manager.login_message_category = 'warning'

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

    test_app.config['MARKDOWN_FOLDER'] = str(posts_dir)

    yield test_app


@pytest.fixture(scope='function')
def app_full(tmp_path):
    """创建完整的测试应用（使用 create_app 工厂）"""
    posts_dir = tmp_path / 'posts'
    posts_dir.mkdir()

    # 临时注入测试配置到 config 字典
    from config import config as config_dict
    config_dict['testing'] = TestConfig
    TestConfig.MARKDOWN_FOLDER = str(posts_dir)

    test_app = create_app('testing')
    test_app.config['MARKDOWN_FOLDER'] = str(posts_dir)

    # 清理
    yield test_app
    config_dict.pop('testing', None)


@pytest.fixture(scope='function')
def db(app_full):
    """创建测试数据库"""
    with app_full.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app_full, db):
    """创建测试客户端"""
    return app_full.test_client()


@pytest.fixture(scope='function')
def runner(app_full, db):
    """创建 CLI 测试 runner"""
    return app_full.test_cli_runner()


# ==================== 数据 Fixtures ====================

@pytest.fixture
def admin_user(db):
    """创建管理员用户"""
    user = User(username='admin', email='admin@test.com', is_admin=True)
    user.set_password('admin123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def normal_user(db):
    """创建普通用户"""
    user = User(username='testuser', email='user@test.com', is_admin=False)
    user.set_password('test123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_category(db):
    """创建示例分类"""
    cat = Category(name='技术', slug='tech', icon='💻', color='#3498db',
                   description='技术文章', order=0)
    db.session.add(cat)
    db.session.commit()
    return cat


@pytest.fixture
def sample_categories(db):
    """创建多个示例分类"""
    cats = []
    data = [
        {'name': '技术', 'slug': 'tech', 'icon': '💻', 'color': '#3498db', 'order': 0},
        {'name': '生活', 'slug': 'life', 'icon': '🌟', 'color': '#2ecc71', 'order': 1},
        {'name': '教程', 'slug': 'tutorial', 'icon': '📚', 'color': '#e74c3c', 'order': 2},
    ]
    for d in data:
        cat = Category(**d)
        db.session.add(cat)
        cats.append(cat)
    db.session.commit()
    return cats


@pytest.fixture
def sample_post(db, admin_user, sample_category):
    """创建示例文章"""
    post = Post(
        title='测试文章',
        slug='test-post',
        content='# 测试\n\n这是一篇测试文章的内容。',
        summary='这是一篇测试文章',
        is_published=True,
        is_from_file=False,
        author_id=admin_user.id
    )
    post.categories.append(sample_category)
    db.session.add(post)
    db.session.commit()
    return post


@pytest.fixture
def sample_posts(db, admin_user, sample_categories):
    """创建多篇示例文章"""
    posts = []
    for i in range(8):
        post = Post(
            title=f'文章 {i+1}',
            slug=f'post-{i+1}',
            content=f'# 文章 {i+1}\n\n这是第 {i+1} 篇文章。',
            summary=f'第 {i+1} 篇文章的摘要',
            is_published=True,
            author_id=admin_user.id
        )
        # 轮流分配分类
        post.categories.append(sample_categories[i % len(sample_categories)])
        db.session.add(post)
        posts.append(post)
    db.session.commit()
    return posts


@pytest.fixture
def unpublished_post(db, admin_user):
    """创建未发布的文章"""
    post = Post(
        title='草稿文章',
        slug='draft-post',
        content='这是一篇草稿。',
        summary='草稿摘要',
        is_published=False,
        author_id=admin_user.id
    )
    db.session.add(post)
    db.session.commit()
    return post


# ==================== 认证辅助 ====================

class AuthActions:
    """认证操作辅助类"""

    def __init__(self, client):
        self._client = client

    def login(self, username='admin', password='admin123'):
        return self._client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self._client.get('/logout', follow_redirects=True)

    def register(self, username='newuser', email='new@test.com',
                 password='newpass123', confirm_password='newpass123'):
        return self._client.post('/register', data={
            'username': username,
            'email': email,
            'password': password,
            'confirm_password': confirm_password
        }, follow_redirects=True)


@pytest.fixture
def auth(client):
    """认证操作辅助 fixture"""
    return AuthActions(client)


# ==================== Markdown 文件 Fixtures ====================

@pytest.fixture
def posts_dir(app_full):
    """返回测试 posts 文件夹路径"""
    return app_full.config['MARKDOWN_FOLDER']


@pytest.fixture
def sample_md_files(posts_dir):
    """在 posts 文件夹中创建示例 Markdown 文件"""
    # 创建子文件夹
    tech_dir = os.path.join(posts_dir, '技术')
    life_dir = os.path.join(posts_dir, '生活')
    os.makedirs(tech_dir, exist_ok=True)
    os.makedirs(life_dir, exist_ok=True)

    files = {}

    # 带 front matter 的文件
    content1 = """---
title: Flask 入门指南
date: 2026-01-15
category: 技术
tags: python, flask, web
summary: 一篇 Flask 入门教程
---

# Flask 入门指南

Flask 是一个轻量级的 Python Web 框架。

## 安装

```bash
pip install flask
```

## 第一个应用

```python
from flask import Flask
app = Flask(__name__)
```
"""
    path1 = os.path.join(tech_dir, 'flask-guide.md')
    with open(path1, 'w', encoding='utf-8') as f:
        f.write(content1)
    files['flask_guide'] = path1

    # 无 front matter 的文件
    content2 = """# 生活随笔

今天天气不错，适合写代码。

- 项目 A 进展顺利
- 学了新的设计模式
"""
    path2 = os.path.join(life_dir, 'daily-notes.md')
    with open(path2, 'w', encoding='utf-8') as f:
        f.write(content2)
    files['daily_notes'] = path2

    # 根目录下的文件
    content3 = """---
title: 通用文章
date: 2026-02-01
---

这是一篇未分类文章。
"""
    path3 = os.path.join(posts_dir, 'general.md')
    with open(path3, 'w', encoding='utf-8') as f:
        f.write(content3)
    files['general'] = path3

    return files
