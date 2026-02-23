"""认证路由单元测试"""
import pytest
from models import User


class TestLogin:
    """登录测试"""

    def test_login_page_loads(self, client):
        """测试登录页面加载"""
        resp = client.get('/login')
        assert resp.status_code == 200
        assert '登录' in resp.data.decode('utf-8')

    def test_login_success(self, client, admin_user, auth):
        """测试登录成功"""
        resp = auth.login('admin', 'admin123')
        assert resp.status_code == 200
        data = resp.data.decode('utf-8')
        assert '登录成功' in data or 'admin' in data

    def test_login_wrong_password(self, client, admin_user, auth):
        """测试密码错误"""
        resp = auth.login('admin', 'wrongpass')
        data = resp.data.decode('utf-8')
        assert '用户名或密码错误' in data

    def test_login_nonexistent_user(self, client, auth):
        """测试用户不存在"""
        resp = auth.login('nobody', 'pass123')
        data = resp.data.decode('utf-8')
        assert '用户名或密码错误' in data

    def test_login_redirect_when_authenticated(self, client, admin_user, auth):
        """测试已登录用户访问登录页被重定向"""
        auth.login('admin', 'admin123')
        resp = client.get('/login')
        assert resp.status_code == 302  # 重定向到首页

    def test_login_with_remember(self, client, admin_user):
        """测试记住我功能"""
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'remember': 'on'
        }, follow_redirects=True)
        assert resp.status_code == 200


class TestRegister:
    """注册测试"""

    def test_register_page_loads(self, client):
        """测试注册页面加载"""
        resp = client.get('/register')
        assert resp.status_code == 200
        assert '注册' in resp.data.decode('utf-8')

    def test_register_success(self, client, auth, db, app_full):
        """测试注册成功"""
        resp = auth.register('newuser', 'new@test.com', 'newpass123', 'newpass123')
        assert resp.status_code == 200
        data = resp.data.decode('utf-8')
        assert '注册成功' in data

        # 验证用户已创建
        with app_full.app_context():
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.email == 'new@test.com'

    def test_register_first_user_is_admin(self, client, db, app_full):
        """测试第一个注册用户自动成为管理员"""
        client.post('/register', data={
            'username': 'firstuser',
            'email': 'first@test.com',
            'password': 'pass123456',
            'confirm_password': 'pass123456'
        }, follow_redirects=True)

        with app_full.app_context():
            user = User.query.filter_by(username='firstuser').first()
            assert user is not None
            assert user.is_admin is True

    def test_register_short_username(self, client, auth):
        """测试用户名太短"""
        resp = auth.register('a', 'a@test.com', 'pass123', 'pass123')
        data = resp.data.decode('utf-8')
        assert '用户名至少需要2个字符' in data

    def test_register_invalid_email(self, client, auth):
        """测试无效邮箱"""
        resp = auth.register('user2', 'invalid-email', 'pass123', 'pass123')
        data = resp.data.decode('utf-8')
        assert '请输入有效的邮箱地址' in data

    def test_register_short_password(self, client, auth):
        """测试密码太短"""
        resp = auth.register('user3', 'u3@test.com', '12345', '12345')
        data = resp.data.decode('utf-8')
        assert '密码至少需要6个字符' in data

    def test_register_password_mismatch(self, client, auth):
        """测试两次密码不一致"""
        resp = auth.register('user4', 'u4@test.com', 'pass123', 'different')
        data = resp.data.decode('utf-8')
        assert '两次输入的密码不一致' in data

    def test_register_duplicate_username(self, client, admin_user, auth):
        """测试重复用户名"""
        resp = auth.register('admin', 'other@test.com', 'pass123', 'pass123')
        data = resp.data.decode('utf-8')
        assert '用户名已存在' in data

    def test_register_duplicate_email(self, client, admin_user, auth):
        """测试重复邮箱"""
        resp = auth.register('unique', 'admin@test.com', 'pass123', 'pass123')
        data = resp.data.decode('utf-8')
        assert '邮箱已被注册' in data

    def test_register_redirect_when_authenticated(self, client, admin_user, auth):
        """测试已登录用户访问注册页被重定向"""
        auth.login('admin', 'admin123')
        resp = client.get('/register')
        assert resp.status_code == 302


class TestLogout:
    """登出测试"""

    def test_logout(self, client, admin_user, auth):
        """测试登出"""
        auth.login('admin', 'admin123')
        resp = auth.logout()
        data = resp.data.decode('utf-8')
        assert '已退出登录' in data

    def test_logout_requires_login(self, client):
        """测试未登录时登出重定向到登录页"""
        resp = client.get('/logout')
        assert resp.status_code == 302
        assert 'login' in resp.headers.get('Location', '')


class TestProfile:
    """个人资料测试"""

    def test_profile_page_loads(self, client, admin_user, auth):
        """测试个人资料页面"""
        auth.login('admin', 'admin123')
        resp = client.get('/profile')
        assert resp.status_code == 200
        data = resp.data.decode('utf-8')
        assert 'admin' in data

    def test_profile_requires_login(self, client):
        """测试未登录访问个人资料重定向"""
        resp = client.get('/profile')
        assert resp.status_code == 302

    def test_update_profile(self, client, admin_user, auth, db, app_full):
        """测试更新个人资料"""
        auth.login('admin', 'admin123')
        resp = client.post('/profile', data={
            'bio': '我是管理员',
            'avatar': 'https://example.com/avatar.png'
        }, follow_redirects=True)
        assert resp.status_code == 200

        with app_full.app_context():
            user = User.query.filter_by(username='admin').first()
            assert user.bio == '我是管理员'
            assert user.avatar == 'https://example.com/avatar.png'
