"""Markdown 文件扫描与解析工具"""
import os
import re
import hashlib
from datetime import datetime


def parse_front_matter(content):
    """解析 Markdown 文件的 front matter (YAML 头部元数据)

    支持格式:
    ---
    title: 文章标题
    date: 2026-01-01
    category: 技术
    tags: python, flask
    summary: 文章摘要
    cover: /static/img/cover.jpg
    ---
    """
    metadata = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            meta_text = parts[1].strip()
            body = parts[2].strip()
            for line in meta_text.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip().lower()] = value.strip()
            return metadata, body
    return metadata, content


def generate_slug(title):
    """从标题生成 URL slug"""
    # 移除特殊字符，用连字符替换空格
    slug = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', title)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = slug.strip('-').lower()
    if not slug:
        slug = hashlib.md5(title.encode()).hexdigest()[:12]
    return slug


def generate_summary(content, max_length=200):
    """从内容生成摘要"""
    # 移除 Markdown 格式标记
    text = re.sub(r'#+ ', '', content)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[*_`~]', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = text.strip()
    if len(text) > max_length:
        return text[:max_length] + '...'
    return text


def scan_markdown_folder(folder_path):
    """扫描指定文件夹下的所有 Markdown 文件

    返回: list[dict] 包含文件信息的列表
    每个 dict 包含: title, slug, content, summary, category, file_path, created_at, updated_at
    """
    posts = []

    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return posts

    for root, dirs, files in os.walk(folder_path):
        # 获取相对于 posts 文件夹的路径作为分类
        rel_path = os.path.relpath(root, folder_path)
        category = rel_path if rel_path != '.' else '未分类'

        for filename in files:
            if not filename.endswith(('.md', '.markdown')):
                continue

            file_path = os.path.join(root, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
            except Exception:
                continue

            metadata, content = parse_front_matter(raw_content)

            # 获取文件修改时间
            file_stat = os.stat(file_path)
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            file_ctime = datetime.fromtimestamp(file_stat.st_ctime)

            title = metadata.get('title', filename.rsplit('.', 1)[0].replace('-', ' ').replace('_', ' ').title())
            slug = metadata.get('slug', generate_slug(title))
            summary = metadata.get('summary', generate_summary(content))
            cover = metadata.get('cover', '')

            # 解析日期
            date_str = metadata.get('date', '')
            try:
                created_at = datetime.strptime(date_str, '%Y-%m-%d') if date_str else file_ctime
            except ValueError:
                created_at = file_ctime

            # 分类可以从 front matter 或文件夹名称获取
            post_category = metadata.get('category', category)
            tags = [t.strip() for t in metadata.get('tags', '').split(',') if t.strip()]

            posts.append({
                'title': title,
                'slug': slug,
                'content': content,
                'raw_content': raw_content,
                'summary': summary,
                'cover_image': cover,
                'category': post_category,
                'tags': tags,
                'file_path': file_path,
                'created_at': created_at,
                'updated_at': file_mtime
            })

    # 按创建时间倒序排列
    posts.sort(key=lambda x: x['created_at'], reverse=True)
    return posts


def get_categories_from_folder(folder_path):
    """从文件夹结构中获取分类列表"""
    categories = set()

    if not os.path.exists(folder_path):
        return list(categories)

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            categories.add(item)

    return sorted(categories)
