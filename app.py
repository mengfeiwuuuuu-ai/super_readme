"""MyBlob 博客系统 - 主应用"""
import os
import re
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, abort, session)
from flask_login import (LoginManager, login_user, logout_user,
                          login_required, current_user)
import markdown
from markupsafe import Markup

from config import config
from models import db, User, Post, Category, post_categories
from utils.markdown_scanner import (scan_markdown_folder, get_categories_from_folder,
                                     generate_slug, generate_summary)
from utils.github_proxy import GitHubProxy

# ==================== 应用工厂 ====================

def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 初始化扩展
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Markdown 渲染器
    md = markdown.Markdown(extensions=[
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.tables',
        'markdown.extensions.toc',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists',
        'markdown.extensions.attr_list',
        'markdown.extensions.meta',
    ], extension_configs={
        'markdown.extensions.codehilite': {
            'css_class': 'highlight',
            'linenums': False
        }
    })

    def render_markdown(text):
        """渲染 Markdown 为 HTML"""
        md.reset()
        html = md.convert(text)
        return Markup(html)

    app.jinja_env.filters['markdown'] = render_markdown

    # 上下文处理器
    @app.context_processor
    def inject_globals():
        categories = Category.query.order_by(Category.order).all()
        current_theme = 'light'
        if current_user.is_authenticated:
            current_theme = current_user.theme or 'light'
        elif 'theme' in session:
            current_theme = session['theme']
        return {
            'blog_title': app.config['BLOG_TITLE'],
            'blog_subtitle': app.config['BLOG_SUBTITLE'],
            'all_categories': categories,
            'current_theme': current_theme,
            'available_themes': app.config['THEMES'],
            'current_year': datetime.utcnow().year
        }

    # ==================== 自动同步 Markdown 文件 ====================

    def _auto_sync_markdown():
        """自动扫描 posts 文件夹，将新文件同步到数据库"""
        folder = app.config['MARKDOWN_FOLDER']
        if not os.path.exists(folder):
            return

        scanned = scan_markdown_folder(folder)
        changed = False

        # 收集数据库中所有来自文件的文章路径
        existing_paths = {p.file_path: p for p in Post.query.filter_by(is_from_file=True).all()}

        for item in scanned:
            fp = item['file_path']
            if fp in existing_paths:
                # 已存在 -> 检查是否需要更新（文件修改时间更新）
                post = existing_paths[fp]
                if item['updated_at'] > post.updated_at:
                    post.title = item['title']
                    post.content = item['content']
                    post.summary = item['summary']
                    post.cover_image = item['cover_image']
                    post.updated_at = item['updated_at']
                    changed = True
            else:
                # 新文件 -> 创建文章
                slug = item['slug']
                if Post.query.filter_by(slug=slug).first():
                    slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

                admin = User.query.filter_by(is_admin=True).first()
                author_id = admin.id if admin else None

                post = Post(
                    title=item['title'],
                    slug=slug,
                    content=item['content'],
                    summary=item['summary'],
                    cover_image=item['cover_image'],
                    is_published=True,
                    is_from_file=True,
                    file_path=fp,
                    author_id=author_id,
                    created_at=item['created_at'],
                    updated_at=item['updated_at']
                )
                db.session.add(post)

                # 处理分类
                cat_name = item['category']
                if cat_name and cat_name != '未分类':
                    cat = Category.query.filter_by(name=cat_name).first()
                    if not cat:
                        cat = Category(name=cat_name, slug=generate_slug(cat_name))
                        db.session.add(cat)
                        db.session.flush()
                    post.categories.append(cat)

                changed = True

        # 删除数据库中已不存在的文件对应的文章
        scanned_paths = {item['file_path'] for item in scanned}
        for fp, post in existing_paths.items():
            if fp not in scanned_paths:
                db.session.delete(post)
                changed = True

        if changed:
            db.session.commit()

    @app.before_request
    def before_request_sync():
        """每次请求前自动同步 Markdown 文件（有节流）"""
        # 仅对页面请求做同步，跳过静态文件和 API
        if request.path.startswith('/static') or request.path.startswith('/api/'):
            return
        # 简单节流：每 5 秒最多同步一次
        import time
        now = time.time()
        last_sync = getattr(app, '_last_md_sync', 0)
        if now - last_sync > 5:
            app._last_md_sync = now
            try:
                _auto_sync_markdown()
            except Exception:
                pass  # 同步失败不影响正常请求

    # GitHub 代理实例
    github = GitHubProxy(token=os.environ.get('GITHUB_TOKEN'))

    # ==================== 管理员装饰器 ====================

    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function

    # ==================== 首页路由 ====================

    @app.route('/')
    def index():
        page = request.args.get('page', 1, type=int)
        category_slug = request.args.get('category', '')
        search_q = request.args.get('q', '')

        query = Post.query.filter_by(is_published=True)

        if category_slug:
            category = Category.query.filter_by(slug=category_slug).first()
            if category:
                query = query.filter(Post.categories.any(Category.id == category.id))

        if search_q:
            query = query.filter(
                db.or_(
                    Post.title.contains(search_q),
                    Post.content.contains(search_q),
                    Post.summary.contains(search_q)
                )
            )

        pagination = query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False
        )
        posts = pagination.items

        return render_template('index.html',
                             posts=posts,
                             pagination=pagination,
                             current_category=category_slug,
                             search_query=search_q)

    # ==================== 文章路由 ====================

    @app.route('/post/<slug>')
    def view_post(slug):
        post = Post.query.filter_by(slug=slug, is_published=True).first_or_404()
        post.view_count += 1
        db.session.commit()
        html_content = render_markdown(post.content)
        return render_template('post.html', post=post, html_content=html_content)

    @app.route('/category/<slug>')
    def view_category(slug):
        category = Category.query.filter_by(slug=slug).first_or_404()
        page = request.args.get('page', 1, type=int)
        pagination = Post.query.filter(
            Post.is_published == True,
            Post.categories.any(Category.id == category.id)
        ).order_by(Post.created_at.desc()).paginate(
            page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False
        )
        return render_template('category.html',
                             category=category,
                             posts=pagination.items,
                             pagination=pagination)

    # ==================== 认证路由 ====================

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember = request.form.get('remember', False)

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user, remember=bool(remember))
                flash('登录成功！', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                flash('用户名或密码错误', 'danger')

        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm = request.form.get('confirm_password', '')

            errors = []
            if not username or len(username) < 2:
                errors.append('用户名至少需要2个字符')
            if not email or '@' not in email:
                errors.append('请输入有效的邮箱地址')
            if len(password) < 6:
                errors.append('密码至少需要6个字符')
            if password != confirm:
                errors.append('两次输入的密码不一致')
            if User.query.filter_by(username=username).first():
                errors.append('用户名已存在')
            if User.query.filter_by(email=email).first():
                errors.append('邮箱已被注册')

            if errors:
                for err in errors:
                    flash(err, 'danger')
            else:
                user = User(username=username, email=email)
                user.set_password(password)
                # 第一个注册的用户自动成为管理员
                if User.query.count() == 0:
                    user.is_admin = True
                db.session.add(user)
                db.session.commit()
                flash('注册成功，请登录！', 'success')
                return redirect(url_for('login'))

        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('已退出登录', 'info')
        return redirect(url_for('index'))

    # ==================== 主题切换 ====================

    @app.route('/api/theme', methods=['POST'])
    def switch_theme():
        theme = request.json.get('theme', 'light')
        if theme not in app.config['THEMES']:
            return jsonify({'success': False, 'error': '无效的主题'}), 400

        session['theme'] = theme
        if current_user.is_authenticated:
            current_user.theme = theme
            db.session.commit()

        return jsonify({'success': True, 'theme': theme})

    # ==================== 管理后台 ====================

    @app.route('/admin')
    @login_required
    @admin_required
    def admin_dashboard():
        stats = {
            'total_posts': Post.query.count(),
            'published_posts': Post.query.filter_by(is_published=True).count(),
            'total_categories': Category.query.count(),
            'total_users': User.query.count(),
            'total_views': db.session.query(db.func.sum(Post.view_count)).scalar() or 0
        }
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
        return render_template('admin.html', stats=stats, recent_posts=recent_posts)

    # ==================== 文章编辑器 ====================

    @app.route('/editor', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def editor():
        post_id = request.args.get('id', type=int)
        post = None
        if post_id:
            post = Post.query.get_or_404(post_id)

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '')
            summary = request.form.get('summary', '').strip()
            category_ids = request.form.getlist('categories', type=int)
            is_published = request.form.get('is_published') == 'on'
            cover_image = request.form.get('cover_image', '').strip()

            if not title:
                flash('标题不能为空', 'danger')
                return render_template('editor.html', post=post)

            if post:
                post.title = title
                post.content = content
                post.summary = summary or generate_summary(content)
                post.cover_image = cover_image
                post.is_published = is_published
                post.updated_at = datetime.utcnow()
            else:
                slug = generate_slug(title)
                # 确保 slug 唯一
                existing = Post.query.filter_by(slug=slug).first()
                if existing:
                    slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
                post = Post(
                    title=title,
                    slug=slug,
                    content=content,
                    summary=summary or generate_summary(content),
                    cover_image=cover_image,
                    is_published=is_published,
                    author_id=current_user.id
                )
                db.session.add(post)

            # 更新分类
            post.categories = Category.query.filter(Category.id.in_(category_ids)).all()
            db.session.commit()
            flash('文章保存成功！', 'success')
            return redirect(url_for('view_post', slug=post.slug))

        categories = Category.query.order_by(Category.order).all()
        return render_template('editor.html', post=post, categories=categories)

    @app.route('/admin/post/delete/<int:post_id>', methods=['POST'])
    @login_required
    @admin_required
    def delete_post(post_id):
        post = Post.query.get_or_404(post_id)
        db.session.delete(post)
        db.session.commit()
        flash('文章已删除', 'info')
        return redirect(url_for('admin_dashboard'))

    # ==================== 分类管理 ====================

    @app.route('/admin/categories', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def manage_categories():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            color = request.form.get('color', '#3498db').strip()
            icon = request.form.get('icon', '📁').strip()

            if not name:
                flash('分类名称不能为空', 'danger')
            elif Category.query.filter_by(name=name).first():
                flash('分类已存在', 'warning')
            else:
                slug = generate_slug(name)
                cat = Category(name=name, slug=slug, description=description,
                              color=color, icon=icon, order=Category.query.count())
                db.session.add(cat)
                db.session.commit()
                flash(f'分类「{name}」创建成功', 'success')

        categories = Category.query.order_by(Category.order).all()
        return render_template('categories_admin.html', categories=categories)

    @app.route('/admin/category/delete/<int:cat_id>', methods=['POST'])
    @login_required
    @admin_required
    def delete_category(cat_id):
        cat = Category.query.get_or_404(cat_id)
        db.session.delete(cat)
        db.session.commit()
        flash('分类已删除', 'info')
        return redirect(url_for('manage_categories'))

    # ==================== 用户管理 ====================

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        if request.method == 'POST':
            bio = request.form.get('bio', '').strip()
            avatar = request.form.get('avatar', '').strip()
            current_user.bio = bio
            current_user.avatar = avatar
            db.session.commit()
            flash('个人资料已更新', 'success')
        return render_template('profile.html')

    @app.route('/admin/users')
    @login_required
    @admin_required
    def manage_users():
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('users_admin.html', users=users)

    @app.route('/admin/user/toggle-admin/<int:user_id>', methods=['POST'])
    @login_required
    @admin_required
    def toggle_admin(user_id):
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('不能修改自己的管理员权限', 'warning')
        else:
            user.is_admin = not user.is_admin
            db.session.commit()
            status = '授予' if user.is_admin else '撤销'
            flash(f'已{status} {user.username} 的管理员权限', 'success')
        return redirect(url_for('manage_users'))

    # ==================== Markdown 文件扫描与同步 ====================

    @app.route('/admin/sync-posts', methods=['POST'])
    @login_required
    @admin_required
    def sync_markdown_posts():
        """从 posts 文件夹同步 Markdown 文件到数据库"""
        folder = app.config['MARKDOWN_FOLDER']
        scanned = scan_markdown_folder(folder)

        created = 0
        updated = 0
        for item in scanned:
            existing = Post.query.filter_by(file_path=item['file_path']).first()
            if existing:
                # 如果文件修改时间更新，则同步内容
                if item['updated_at'] > existing.updated_at:
                    existing.title = item['title']
                    existing.content = item['content']
                    existing.summary = item['summary']
                    existing.updated_at = item['updated_at']
                    updated += 1
            else:
                # 创建新文章
                slug = item['slug']
                if Post.query.filter_by(slug=slug).first():
                    slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

                post = Post(
                    title=item['title'],
                    slug=slug,
                    content=item['content'],
                    summary=item['summary'],
                    cover_image=item['cover_image'],
                    is_published=True,
                    is_from_file=True,
                    file_path=item['file_path'],
                    author_id=current_user.id,
                    created_at=item['created_at'],
                    updated_at=item['updated_at']
                )
                db.session.add(post)

                # 处理分类
                cat_name = item['category']
                if cat_name and cat_name != '未分类':
                    cat = Category.query.filter_by(name=cat_name).first()
                    if not cat:
                        cat = Category(name=cat_name, slug=generate_slug(cat_name))
                        db.session.add(cat)
                        db.session.flush()
                    post.categories.append(cat)

                created += 1

        db.session.commit()
        flash(f'同步完成：新增 {created} 篇，更新 {updated} 篇', 'success')
        return redirect(url_for('admin_dashboard'))

    # ==================== GitHub 代理路由 ====================

    @app.route('/github')
    def github_page():
        return render_template('github.html')

    @app.route('/api/github/repo/<owner>/<repo>')
    def github_repo_info(owner, repo):
        result = github.get_repo_info(owner, repo)
        return jsonify(result)

    @app.route('/api/github/readme/<owner>/<repo>')
    def github_readme(owner, repo):
        branch = request.args.get('branch', 'main')
        result = github.get_readme(owner, repo, branch)
        if result['success']:
            result['html'] = render_markdown(result['content'])
        return jsonify(result)

    @app.route('/api/github/file/<owner>/<repo>/<path:filepath>')
    def github_file(owner, repo, filepath):
        branch = request.args.get('branch', 'main')
        result = github.get_file_content(owner, repo, filepath, branch)
        if result['success'] and filepath.endswith(('.md', '.markdown')):
            result['html'] = render_markdown(result['content'])
        return jsonify(result)

    @app.route('/api/github/search')
    def github_search():
        query = request.args.get('q', '')
        if not query:
            return jsonify({'success': False, 'error': '请输入搜索关键词'})
        result = github.search_repos(query)
        return jsonify(result)

    @app.route('/api/github/user/<username>/repos')
    def github_user_repos(username):
        result = github.get_user_repos(username)
        return jsonify(result)

    # ==================== API 路由 ====================

    @app.route('/api/posts')
    def api_posts():
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        pagination = Post.query.filter_by(is_published=True).order_by(
            Post.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'posts': [p.to_dict() for p in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })

    @app.route('/api/markdown/preview', methods=['POST'])
    @login_required
    def markdown_preview():
        content = request.json.get('content', '')
        html = render_markdown(content)
        return jsonify({'html': str(html)})

    # ==================== 错误处理 ====================

    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', code=404, message='页面未找到'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html', code=403, message='没有权限访问'), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', code=500, message='服务器内部错误'), 500

    return app


# ==================== 数据库初始化 ====================

def init_db(app):
    """初始化数据库，创建表和默认数据"""
    with app.app_context():
        db.create_all()

        # 创建默认分类
        default_categories = [
            {'name': '技术', 'slug': 'tech', 'icon': '💻', 'color': '#3498db', 'description': '技术文章与教程'},
            {'name': '生活', 'slug': 'life', 'icon': '🌟', 'color': '#2ecc71', 'description': '生活随笔与感悟'},
            {'name': '教程', 'slug': 'tutorial', 'icon': '📚', 'color': '#e74c3c', 'description': '学习教程与笔记'},
            {'name': '项目', 'slug': 'project', 'icon': '🚀', 'color': '#9b59b6', 'description': '项目展示与记录'},
        ]

        for cat_data in default_categories:
            if not Category.query.filter_by(slug=cat_data['slug']).first():
                cat = Category(**cat_data, order=default_categories.index(cat_data))
                db.session.add(cat)

        db.session.commit()

        # 自动扫描 posts 文件夹中的 Markdown 文件
        folder = app.config['MARKDOWN_FOLDER']
        if os.path.exists(folder):
            scanned = scan_markdown_folder(folder)
            for item in scanned:
                if not Post.query.filter_by(file_path=item['file_path']).first():
                    slug = item['slug']
                    if Post.query.filter_by(slug=slug).first():
                        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

                    # 使用管理员用户或第一个用户
                    admin = User.query.filter_by(is_admin=True).first()
                    author_id = admin.id if admin else None

                    post = Post(
                        title=item['title'],
                        slug=slug,
                        content=item['content'],
                        summary=item['summary'],
                        cover_image=item['cover_image'],
                        is_published=True,
                        is_from_file=True,
                        file_path=item['file_path'],
                        author_id=author_id,
                        created_at=item['created_at'],
                        updated_at=item['updated_at']
                    )
                    db.session.add(post)

                    # 分类
                    cat_name = item['category']
                    if cat_name and cat_name != '未分类':
                        cat = Category.query.filter_by(name=cat_name).first()
                        if not cat:
                            cat = Category(name=cat_name, slug=generate_slug(cat_name))
                            db.session.add(cat)
                            db.session.flush()
                        post.categories.append(cat)

            db.session.commit()


# ==================== 入口 ====================

app = create_app(os.environ.get('FLASK_CONFIG', 'default'))

if __name__ == '__main__':
    init_db(app)
    print("=" * 50)
    print(f"  {app.config['BLOG_TITLE']} 已启动!")
    print(f"  访问地址: http://127.0.0.1:5000")
    print(f"  管理后台: http://127.0.0.1:5000/admin")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
