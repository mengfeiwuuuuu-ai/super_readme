"""API 路由单元测试"""
import json
import pytest


class TestThemeAPI:
    """主题切换 API 测试"""

    def test_switch_theme(self, client):
        """测试切换主题"""
        resp = client.post('/api/theme',
                          data=json.dumps({'theme': 'dark'}),
                          content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['theme'] == 'dark'

    def test_switch_to_all_themes(self, client):
        """测试切换到所有可用主题"""
        for theme in ['light', 'dark', 'ocean', 'forest', 'sunset']:
            resp = client.post('/api/theme',
                              data=json.dumps({'theme': theme}),
                              content_type='application/json')
            assert resp.status_code == 200
            assert resp.get_json()['theme'] == theme

    def test_switch_invalid_theme(self, client):
        """测试切换到无效主题"""
        resp = client.post('/api/theme',
                          data=json.dumps({'theme': 'invalid_theme'}),
                          content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_theme_saved_for_user(self, client, admin_user, auth, db, app_full):
        """测试已登录用户的主题偏好被保存"""
        auth.login('admin', 'admin123')
        client.post('/api/theme',
                    data=json.dumps({'theme': 'ocean'}),
                    content_type='application/json')

        with app_full.app_context():
            from models import User
            user = User.query.filter_by(username='admin').first()
            assert user.theme == 'ocean'


class TestPostsAPI:
    """文章列表 API 测试"""

    def test_get_posts(self, client, sample_posts):
        """测试获取文章列表"""
        resp = client.get('/api/posts')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'posts' in data
        assert 'total' in data
        assert 'pages' in data
        assert data['total'] == 8

    def test_get_posts_pagination(self, client, sample_posts):
        """测试文章分页"""
        resp = client.get('/api/posts?page=1&per_page=3')
        data = resp.get_json()
        assert len(data['posts']) == 3
        assert data['total'] == 8

    def test_get_posts_empty(self, client):
        """测试无文章时返回空列表"""
        resp = client.get('/api/posts')
        data = resp.get_json()
        assert data['posts'] == []
        assert data['total'] == 0

    def test_posts_contain_required_fields(self, client, sample_post):
        """测试文章数据包含必要字段"""
        resp = client.get('/api/posts')
        data = resp.get_json()
        post = data['posts'][0]
        required_fields = ['id', 'title', 'slug', 'summary', 'author', 'categories', 'created_at']
        for field in required_fields:
            assert field in post, f"缺少字段: {field}"


class TestMarkdownPreviewAPI:
    """Markdown 预览 API 测试"""

    def test_preview_markdown(self, client, admin_user, auth):
        """测试 Markdown 预览"""
        auth.login('admin', 'admin123')
        resp = client.post('/api/markdown/preview',
                          data=json.dumps({'content': '# 标题\n\n**加粗**'}),
                          content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert '<h1>' in data['html'] or '标题' in data['html']
        assert '<strong>' in data['html']

    def test_preview_requires_login(self, client):
        """测试预览需要登录"""
        resp = client.post('/api/markdown/preview',
                          data=json.dumps({'content': '# Test'}),
                          content_type='application/json')
        assert resp.status_code == 302  # 重定向到登录

    def test_preview_code_block(self, client, admin_user, auth):
        """测试代码块预览"""
        auth.login('admin', 'admin123')
        content = '```python\nprint("hello")\n```'
        resp = client.post('/api/markdown/preview',
                          data=json.dumps({'content': content}),
                          content_type='application/json')
        data = resp.get_json()
        assert 'print' in data['html']

    def test_preview_empty_content(self, client, admin_user, auth):
        """测试空内容预览"""
        auth.login('admin', 'admin123')
        resp = client.post('/api/markdown/preview',
                          data=json.dumps({'content': ''}),
                          content_type='application/json')
        assert resp.status_code == 200


class TestGitHubRoutes:
    """GitHub 代理路由测试"""

    def test_github_page_loads(self, client):
        """测试 GitHub 页面加载"""
        resp = client.get('/github')
        assert resp.status_code == 200
        assert 'GitHub' in resp.data.decode('utf-8')

    def test_github_repo_api(self, client):
        """测试 GitHub 仓库 API 路由存在"""
        # 不实际调用 GitHub API，只检查路由存在
        resp = client.get('/api/github/repo/test/test')
        # 可能返回错误（网络），但路由应存在（不是 404）
        assert resp.status_code != 404

    def test_github_readme_api(self, client):
        """测试 GitHub README API 路由存在"""
        resp = client.get('/api/github/readme/test/test')
        assert resp.status_code != 404

    def test_github_search_api(self, client):
        """测试 GitHub 搜索 API 路由"""
        resp = client.get('/api/github/search')
        assert resp.status_code == 200
        data = resp.get_json()
        # 无搜索词应返回错误
        assert data['success'] is False

    def test_github_search_without_query(self, client):
        """测试无搜索词的 GitHub 搜索"""
        resp = client.get('/api/github/search?q=')
        data = resp.get_json()
        assert data['success'] is False
        assert '请输入搜索关键词' in data['error']

    def test_github_user_repos_api(self, client):
        """测试 GitHub 用户仓库 API 路由存在"""
        resp = client.get('/api/github/user/testuser/repos')
        assert resp.status_code != 404

    def test_github_file_api(self, client):
        """测试 GitHub 文件内容 API 路由存在"""
        resp = client.get('/api/github/file/owner/repo/path/to/file.py')
        assert resp.status_code != 404
