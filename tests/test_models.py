"""数据库模型单元测试"""
import pytest
from models import User, Post, Category, db


class TestUserModel:
    """User 模型测试"""

    def test_create_user(self, db, app_full):
        """测试创建用户"""
        user = User(username='alice', email='alice@test.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.username == 'alice'
        assert user.email == 'alice@test.com'
        assert user.is_admin is False
        assert user.theme == 'light'

    def test_set_and_check_password(self, db, app_full):
        """测试密码哈希与验证"""
        user = User(username='bob', email='bob@test.com')
        user.set_password('secure_pass')
        db.session.add(user)
        db.session.commit()

        assert user.password_hash is not None
        assert user.password_hash != 'secure_pass'  # 不应明文存储
        assert user.check_password('secure_pass') is True
        assert user.check_password('wrong_pass') is False

    def test_password_hash_unique(self, db, app_full):
        """测试相同密码产生不同哈希"""
        user1 = User(username='u1', email='u1@test.com')
        user2 = User(username='u2', email='u2@test.com')
        user1.set_password('samepass')
        user2.set_password('samepass')

        # werkzeug 的 pbkdf2 会使用不同 salt
        assert user1.password_hash != user2.password_hash

    def test_user_to_dict(self, admin_user):
        """测试 User.to_dict()"""
        d = admin_user.to_dict()
        assert d['username'] == 'admin'
        assert d['email'] == 'admin@test.com'
        assert d['is_admin'] is True
        assert 'id' in d
        assert 'created_at' in d
        assert 'password_hash' not in d  # 不应暴露密码哈希

    def test_user_is_authenticated(self, admin_user):
        """测试 UserMixin 的 is_authenticated 属性"""
        assert admin_user.is_authenticated is True
        assert admin_user.is_active is True

    def test_unique_username(self, db, app_full):
        """测试用户名唯一约束"""
        u1 = User(username='unique', email='e1@test.com')
        u1.set_password('pass1')
        db.session.add(u1)
        db.session.commit()

        u2 = User(username='unique', email='e2@test.com')
        u2.set_password('pass2')
        db.session.add(u2)

        with pytest.raises(Exception):
            db.session.commit()

    def test_unique_email(self, db, app_full):
        """测试邮箱唯一约束"""
        u1 = User(username='user_a', email='same@test.com')
        u1.set_password('pass1')
        db.session.add(u1)
        db.session.commit()

        u2 = User(username='user_b', email='same@test.com')
        u2.set_password('pass2')
        db.session.add(u2)

        with pytest.raises(Exception):
            db.session.commit()

    def test_user_default_values(self, db, app_full):
        """测试用户默认值"""
        user = User(username='defaults', email='d@test.com')
        user.set_password('pass')
        db.session.add(user)
        db.session.commit()

        assert user.avatar == ''
        assert user.bio == ''
        assert user.is_admin is False
        assert user.theme == 'light'
        assert user.created_at is not None


class TestCategoryModel:
    """Category 模型测试"""

    def test_create_category(self, sample_category):
        """测试创建分类"""
        assert sample_category.id is not None
        assert sample_category.name == '技术'
        assert sample_category.slug == 'tech'

    def test_category_to_dict(self, sample_category):
        """测试 Category.to_dict()"""
        d = sample_category.to_dict()
        assert d['name'] == '技术'
        assert d['slug'] == 'tech'
        assert d['icon'] == '💻'
        assert d['color'] == '#3498db'
        assert 'id' in d

    def test_unique_category_name(self, db, sample_category):
        """测试分类名称唯一约束"""
        cat2 = Category(name='技术', slug='tech2')
        db.session.add(cat2)
        with pytest.raises(Exception):
            db.session.commit()

    def test_unique_category_slug(self, db, sample_category):
        """测试分类 slug 唯一约束"""
        cat2 = Category(name='技术2', slug='tech')
        db.session.add(cat2)
        with pytest.raises(Exception):
            db.session.commit()

    def test_category_default_values(self, db, app_full):
        """测试分类默认值"""
        cat = Category(name='默认', slug='default')
        db.session.add(cat)
        db.session.commit()

        assert cat.color == '#3498db'
        assert cat.icon == '📁'
        assert cat.order == 0
        assert cat.description == ''


class TestPostModel:
    """Post 模型测试"""

    def test_create_post(self, sample_post):
        """测试创建文章"""
        assert sample_post.id is not None
        assert sample_post.title == '测试文章'
        assert sample_post.slug == 'test-post'
        assert sample_post.is_published is True

    def test_post_author_relationship(self, sample_post, admin_user):
        """测试文章-作者关系"""
        assert sample_post.author is not None
        assert sample_post.author.username == 'admin'
        assert sample_post in admin_user.posts.all()

    def test_post_category_relationship(self, sample_post, sample_category):
        """测试文章-分类多对多关系"""
        assert sample_category in sample_post.categories
        assert sample_post in sample_category.posts.all()

    def test_post_multiple_categories(self, db, admin_user, sample_categories):
        """测试文章属于多个分类"""
        post = Post(
            title='多分类文章', slug='multi-cat',
            content='内容', summary='摘要',
            author_id=admin_user.id
        )
        post.categories.extend(sample_categories[:2])
        db.session.add(post)
        db.session.commit()

        assert len(post.categories) == 2

    def test_post_to_dict(self, sample_post):
        """测试 Post.to_dict()"""
        d = sample_post.to_dict()
        assert d['title'] == '测试文章'
        assert d['slug'] == 'test-post'
        assert d['is_published'] is True
        assert d['author'] == 'admin'
        assert isinstance(d['categories'], list)
        assert len(d['categories']) == 1
        assert 'created_at' in d

    def test_post_to_dict_no_author(self, db, app_full):
        """测试无作者时 to_dict()"""
        post = Post(title='无作者', slug='no-author', content='内容', summary='摘要')
        db.session.add(post)
        db.session.commit()

        d = post.to_dict()
        assert d['author'] == 'Unknown'

    def test_post_view_count(self, sample_post, db):
        """测试文章浏览计数"""
        assert sample_post.view_count == 0
        sample_post.view_count += 1
        db.session.commit()
        assert sample_post.view_count == 1

    def test_unique_slug(self, db, admin_user, sample_post):
        """测试文章 slug 唯一约束"""
        post2 = Post(title='另一篇', slug='test-post', content='内容', summary='摘要',
                      author_id=admin_user.id)
        db.session.add(post2)
        with pytest.raises(Exception):
            db.session.commit()

    def test_post_from_file(self, db, admin_user):
        """测试来自文件的文章"""
        post = Post(
            title='文件文章', slug='file-post',
            content='# 内容', summary='摘要',
            is_from_file=True, file_path='/posts/tech/test.md',
            author_id=admin_user.id
        )
        db.session.add(post)
        db.session.commit()

        assert post.is_from_file is True
        assert post.file_path == '/posts/tech/test.md'

    def test_delete_post(self, db, sample_post):
        """测试删除文章"""
        post_id = sample_post.id
        db.session.delete(sample_post)
        db.session.commit()

        assert Post.query.get(post_id) is None
