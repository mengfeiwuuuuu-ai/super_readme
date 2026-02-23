"""管理后台路由单元测试"""
import os
import pytest
from models import Post, Category, User


class TestAdminDashboard:
    """管理后台首页测试"""

    def test_admin_page_loads(self, client, admin_user, auth):
        """测试管理后台加载"""
        auth.login('admin', 'admin123')
        resp = client.get('/admin')
        assert resp.status_code == 200
        data = resp.data.decode('utf-8')
        assert '管理' in data or 'admin' in data.lower()

    def test_admin_requires_login(self, client):
        """测试未登录无法访问管理后台"""
        resp = client.get('/admin')
        assert resp.status_code == 302

    def test_admin_requires_admin_role(self, client, normal_user, auth):
        """测试普通用户无法访问管理后台"""
        auth.login('testuser', 'test123')
        resp = client.get('/admin')
        assert resp.status_code == 403

    def test_admin_shows_stats(self, client, admin_user, auth, sample_posts):
        """测试管理后台显示统计信息"""
        auth.login('admin', 'admin123')
        resp = client.get('/admin')
        assert resp.status_code == 200


class TestEditor:
    """文章编辑器测试"""

    def test_editor_page_loads(self, client, admin_user, auth):
        """测试编辑器页面加载"""
        auth.login('admin', 'admin123')
        resp = client.get('/editor')
        assert resp.status_code == 200

    def test_create_post(self, client, admin_user, auth, sample_category, db, app_full):
        """测试创建新文章"""
        auth.login('admin', 'admin123')
        resp = client.post('/editor', data={
            'title': '新文章标题',
            'content': '# 新文章\n\n这是内容。',
            'summary': '新文章摘要',
            'categories': [sample_category.id],
            'is_published': 'on'
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app_full.app_context():
            post = Post.query.filter_by(title='新文章标题').first()
            assert post is not None
            assert post.is_published is True
            assert post.author_id == admin_user.id

    def test_create_post_empty_title(self, client, admin_user, auth):
        """测试标题为空时提示错误"""
        auth.login('admin', 'admin123')
        resp = client.post('/editor', data={
            'title': '',
            'content': '内容'
        }, follow_redirects=True)
        data = resp.data.decode('utf-8')
        assert '标题不能为空' in data

    def test_edit_existing_post(self, client, admin_user, auth, sample_post, db, app_full):
        """测试编辑已有文章"""
        auth.login('admin', 'admin123')
        resp = client.post(f'/editor?id={sample_post.id}', data={
            'title': '修改后的标题',
            'content': '修改后的内容',
            'summary': '修改后的摘要',
            'categories': [],
            'is_published': 'on'
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app_full.app_context():
            post = Post.query.get(sample_post.id)
            assert post.title == '修改后的标题'

    def test_editor_requires_admin(self, client, normal_user, auth):
        """测试普通用户无法访问编辑器"""
        auth.login('testuser', 'test123')
        resp = client.get('/editor')
        assert resp.status_code == 403


class TestDeletePost:
    """删除文章测试"""

    def test_delete_post(self, client, admin_user, auth, sample_post, db, app_full):
        """测试删除文章"""
        auth.login('admin', 'admin123')
        post_id = sample_post.id
        resp = client.post(f'/admin/post/delete/{post_id}', follow_redirects=True)
        assert resp.status_code == 200

        with app_full.app_context():
            assert Post.query.get(post_id) is None

    def test_delete_nonexistent_post(self, client, admin_user, auth):
        """测试删除不存在的文章"""
        auth.login('admin', 'admin123')
        resp = client.post('/admin/post/delete/99999')
        assert resp.status_code == 404

    def test_delete_requires_admin(self, client, normal_user, auth, sample_post):
        """测试普通用户无法删除"""
        auth.login('testuser', 'test123')
        resp = client.post(f'/admin/post/delete/{sample_post.id}')
        assert resp.status_code == 403


class TestCategoryManagement:
    """分类管理测试"""

    def test_manage_categories_page(self, client, admin_user, auth):
        """测试分类管理页面"""
        auth.login('admin', 'admin123')
        resp = client.get('/admin/categories')
        assert resp.status_code == 200

    def test_create_category(self, client, admin_user, auth, db, app_full):
        """测试创建分类"""
        auth.login('admin', 'admin123')
        resp = client.post('/admin/categories', data={
            'name': '新分类',
            'description': '描述',
            'color': '#ff0000',
            'icon': '🎯'
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app_full.app_context():
            cat = Category.query.filter_by(name='新分类').first()
            assert cat is not None
            assert cat.color == '#ff0000'

    def test_create_duplicate_category(self, client, admin_user, auth, sample_category):
        """测试创建重复分类"""
        auth.login('admin', 'admin123')
        resp = client.post('/admin/categories', data={
            'name': '技术',
            'description': '重复',
        }, follow_redirects=True)
        data = resp.data.decode('utf-8')
        assert '分类已存在' in data

    def test_create_category_empty_name(self, client, admin_user, auth):
        """测试分类名称为空"""
        auth.login('admin', 'admin123')
        resp = client.post('/admin/categories', data={
            'name': '',
        }, follow_redirects=True)
        data = resp.data.decode('utf-8')
        assert '分类名称不能为空' in data

    def test_delete_category(self, client, admin_user, auth, sample_category, db, app_full):
        """测试删除分类"""
        auth.login('admin', 'admin123')
        cat_id = sample_category.id
        resp = client.post(f'/admin/category/delete/{cat_id}', follow_redirects=True)
        assert resp.status_code == 200

        with app_full.app_context():
            assert Category.query.get(cat_id) is None


class TestUserManagement:
    """用户管理测试"""

    def test_manage_users_page(self, client, admin_user, auth):
        """测试用户管理页面"""
        auth.login('admin', 'admin123')
        resp = client.get('/admin/users')
        assert resp.status_code == 200

    def test_toggle_admin(self, client, admin_user, normal_user, auth, db, app_full):
        """测试切换管理员权限"""
        auth.login('admin', 'admin123')
        resp = client.post(f'/admin/user/toggle-admin/{normal_user.id}',
                          follow_redirects=True)
        assert resp.status_code == 200

        with app_full.app_context():
            user = User.query.get(normal_user.id)
            assert user.is_admin is True

    def test_toggle_own_admin(self, client, admin_user, auth):
        """测试不能修改自己的管理员权限"""
        auth.login('admin', 'admin123')
        resp = client.post(f'/admin/user/toggle-admin/{admin_user.id}',
                          follow_redirects=True)
        data = resp.data.decode('utf-8')
        assert '不能修改自己的管理员权限' in data

    def test_user_management_requires_admin(self, client, normal_user, auth):
        """测试普通用户无法管理用户"""
        auth.login('testuser', 'test123')
        resp = client.get('/admin/users')
        assert resp.status_code == 403


class TestSyncPosts:
    """文章同步测试"""

    def test_sync_posts(self, client, admin_user, auth, sample_md_files, db, app_full):
        """测试手动同步 Markdown 文件"""
        auth.login('admin', 'admin123')
        resp = client.post('/admin/sync-posts', follow_redirects=True)
        assert resp.status_code == 200
        data = resp.data.decode('utf-8')
        assert '同步完成' in data

        # 验证文章已创建
        with app_full.app_context():
            posts = Post.query.filter_by(is_from_file=True).all()
            assert len(posts) >= 1

    def test_sync_requires_admin(self, client, normal_user, auth):
        """测试同步需要管理员权限"""
        auth.login('testuser', 'test123')
        resp = client.post('/admin/sync-posts')
        assert resp.status_code == 403

    def test_sync_creates_categories(self, client, admin_user, auth, sample_md_files, db, app_full):
        """测试同步自动创建分类"""
        auth.login('admin', 'admin123')
        client.post('/admin/sync-posts', follow_redirects=True)

        with app_full.app_context():
            tech_cat = Category.query.filter_by(name='技术').first()
            assert tech_cat is not None
