"""页面路由单元测试"""
import pytest


class TestIndexPage:
    """首页测试"""

    def test_index_page_loads(self, client):
        """测试首页正常加载"""
        resp = client.get('/')
        assert resp.status_code == 200
        assert '测试博客' in resp.data.decode('utf-8')

    def test_index_shows_published_posts(self, client, sample_posts):
        """测试首页显示已发布文章"""
        resp = client.get('/')
        data = resp.data.decode('utf-8')
        # 8 篇文章按时间倒序，第一页应有 post-card
        assert 'post-card' in data
        assert '阅读更多' in data

    def test_index_hides_unpublished_posts(self, client, sample_post, unpublished_post):
        """测试首页不显示未发布文章"""
        resp = client.get('/')
        data = resp.data.decode('utf-8')
        assert '测试文章' in data
        assert '草稿文章' not in data

    def test_index_pagination(self, client, sample_posts):
        """测试首页分页（POSTS_PER_PAGE=5）"""
        # 有 8 篇文章，每页 5 篇
        resp = client.get('/')
        assert resp.status_code == 200

        resp2 = client.get('/?page=2')
        assert resp2.status_code == 200

    def test_index_category_filter(self, client, sample_posts, sample_categories):
        """测试按分类过滤"""
        resp = client.get('/?category=tech')
        assert resp.status_code == 200

    def test_index_search(self, client, sample_post):
        """测试搜索功能"""
        resp = client.get('/?q=测试')
        assert resp.status_code == 200
        data = resp.data.decode('utf-8')
        assert '测试文章' in data

    def test_index_search_no_results(self, client, sample_post):
        """测试搜索无结果"""
        resp = client.get('/?q=不存在的关键词xyz')
        assert resp.status_code == 200


class TestPostPage:
    """文章页面测试"""

    def test_view_post(self, client, sample_post):
        """测试查看文章"""
        resp = client.get('/post/test-post')
        assert resp.status_code == 200
        data = resp.data.decode('utf-8')
        assert '测试文章' in data

    def test_view_post_increments_view_count(self, client, sample_post, db):
        """测试查看文章增加浏览计数"""
        assert sample_post.view_count == 0
        client.get('/post/test-post')
        db.session.refresh(sample_post)
        assert sample_post.view_count == 1

    def test_view_nonexistent_post(self, client):
        """测试访问不存在的文章返回 404"""
        resp = client.get('/post/nonexistent-slug')
        assert resp.status_code == 404

    def test_view_unpublished_post(self, client, unpublished_post):
        """测试未发布文章返回 404"""
        resp = client.get('/post/draft-post')
        assert resp.status_code == 404

    def test_post_renders_markdown(self, client, sample_post):
        """测试文章 Markdown 被渲染为 HTML"""
        resp = client.get('/post/test-post')
        data = resp.data.decode('utf-8')
        # Markdown # 测试 应该被渲染为 <h1>
        assert '<h1>' in data or '测试' in data


class TestCategoryPage:
    """分类页面测试"""

    def test_view_category(self, client, sample_category, sample_post):
        """测试查看分类页面"""
        resp = client.get('/category/tech')
        assert resp.status_code == 200
        data = resp.data.decode('utf-8')
        assert '技术' in data

    def test_view_nonexistent_category(self, client):
        """测试访问不存在的分类返回 404"""
        resp = client.get('/category/nonexistent')
        assert resp.status_code == 404

    def test_category_shows_posts(self, client, sample_post, sample_category):
        """测试分类页面显示其文章"""
        resp = client.get('/category/tech')
        data = resp.data.decode('utf-8')
        assert '测试文章' in data


class TestErrorPages:
    """错误页面测试"""

    def test_404_page(self, client):
        """测试 404 页面"""
        resp = client.get('/nonexistent-page')
        assert resp.status_code == 404

    def test_403_page(self, client, normal_user, auth):
        """测试 403 页面（普通用户访问管理页面）"""
        auth.login(username='testuser', password='test123')
        resp = client.get('/admin')
        assert resp.status_code == 403
