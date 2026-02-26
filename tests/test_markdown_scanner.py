"""Markdown 扫描工具单元测试"""
import os
import pytest

from utils.markdown_scanner import (
    parse_front_matter,
    generate_slug,
    generate_summary,
    scan_markdown_folder,
    get_categories_from_folder
)


class TestParseFrontMatter:
    """front matter 解析测试"""

    def test_parse_valid_front_matter(self):
        """测试解析完整的 front matter"""
        content = """---
title: 我的文章
date: 2026-01-01
category: 技术
tags: python, flask
summary: 这是摘要
---

# 正文内容
这是文章正文。
"""
        metadata, body = parse_front_matter(content)
        assert metadata['title'] == '我的文章'
        assert metadata['date'] == '2026-01-01'
        assert metadata['category'] == '技术'
        assert metadata['tags'] == 'python, flask'
        assert metadata['summary'] == '这是摘要'
        assert '# 正文内容' in body

    def test_parse_no_front_matter(self):
        """测试无 front matter 的内容"""
        content = "# 普通标题\n\n这是正文。"
        metadata, body = parse_front_matter(content)
        assert metadata == {}
        assert body == content

    def test_parse_empty_front_matter(self):
        """测试空的 front matter"""
        content = "---\n---\n\n正文内容"
        metadata, body = parse_front_matter(content)
        assert metadata == {}
        assert '正文内容' in body

    def test_parse_front_matter_with_colons_in_value(self):
        """测试值中包含冒号的情况"""
        content = """---
title: Flask 指南: 从入门到精通
url: https://example.com
---

内容"""
        metadata, body = parse_front_matter(content)
        assert metadata['title'] == 'Flask 指南: 从入门到精通'
        assert metadata['url'] == 'https://example.com'

    def test_parse_front_matter_case_insensitive_keys(self):
        """测试 key 转为小写"""
        content = """---
Title: 大写键
DATE: 2026-01-01
---

内容"""
        metadata, body = parse_front_matter(content)
        assert 'title' in metadata
        assert 'date' in metadata

    def test_incomplete_front_matter(self):
        """测试不完整的 front matter（只有一个 ---）"""
        content = "---\ntitle: 测试\n没有结束标记"
        metadata, body = parse_front_matter(content)
        # 无法正确解析，应返回原始内容
        assert body == content or metadata == {}


class TestGenerateSlug:
    """slug 生成测试"""

    def test_english_title(self):
        """测试英文标题"""
        slug = generate_slug('Hello World')
        assert slug == 'hello-world'

    def test_chinese_title(self):
        """测试中文标题"""
        slug = generate_slug('你好世界')
        assert '你好世界' in slug

    def test_mixed_title(self):
        """测试中英混合标题"""
        slug = generate_slug('Flask 入门')
        assert 'flask' in slug
        assert '入门' in slug

    def test_special_characters_removed(self):
        """测试特殊字符被移除"""
        slug = generate_slug('Hello! World? #Test')
        assert '!' not in slug
        assert '?' not in slug
        assert '#' not in slug

    def test_empty_title_uses_hash(self):
        """测试空标题使用 hash 作为 slug"""
        slug = generate_slug('!@#$%')
        # 特殊字符全部移除后为空，应使用 md5 hash
        assert len(slug) > 0

    def test_spaces_converted_to_hyphens(self):
        """测试空格转换为连字符"""
        slug = generate_slug('one  two   three')
        assert '--' not in slug  # 多个空格应合并
        assert '-' in slug

    def test_leading_trailing_hyphens_stripped(self):
        """测试首尾连字符被去除"""
        slug = generate_slug(' hello ')
        assert not slug.startswith('-')
        assert not slug.endswith('-')


class TestGenerateSummary:
    """摘要生成测试"""

    def test_plain_text(self):
        """测试纯文本摘要"""
        content = "这是一段纯文本内容。"
        summary = generate_summary(content)
        assert summary == "这是一段纯文本内容。"

    def test_strip_headings(self):
        """测试去除 Markdown 标题符号"""
        content = "# 标题\n\n正文内容"
        summary = generate_summary(content)
        assert '#' not in summary
        assert '标题' in summary

    def test_strip_links(self):
        """测试去除 Markdown 链接格式"""
        content = "请访问 [我的网站](https://example.com) 了解更多。"
        summary = generate_summary(content)
        assert '我的网站' in summary
        assert 'https://' not in summary
        assert '[' not in summary

    def test_strip_emphasis(self):
        """测试去除加粗和斜体"""
        content = "这是 **加粗** 和 *斜体* 文本。"
        summary = generate_summary(content)
        assert '*' not in summary
        assert '加粗' in summary

    def test_truncate_long_content(self):
        """测试长内容截断"""
        content = "x" * 300
        summary = generate_summary(content, max_length=200)
        assert len(summary) == 203  # 200 + '...'
        assert summary.endswith('...')

    def test_custom_max_length(self):
        """测试自定义截断长度"""
        content = "x" * 100
        summary = generate_summary(content, max_length=50)
        assert len(summary) == 53  # 50 + '...'

    def test_short_content_no_truncate(self):
        """测试短内容不截断"""
        content = "短内容"
        summary = generate_summary(content)
        assert summary == "短内容"
        assert '...' not in summary

    def test_strip_images(self):
        """测试去除图片"""
        content = "文字 ![图片](img.png) 更多文字"
        summary = generate_summary(content)
        assert '![' not in summary
        assert 'img.png' not in summary


class TestScanMarkdownFolder:
    """Markdown 文件夹扫描测试"""

    def test_scan_with_files(self, sample_md_files, posts_dir):
        """测试扫描有文件的文件夹"""
        posts = scan_markdown_folder(posts_dir)
        assert len(posts) == 3

    def test_scanned_post_fields(self, sample_md_files, posts_dir):
        """测试扫描结果包含必要字段"""
        posts = scan_markdown_folder(posts_dir)
        required_fields = ['title', 'slug', 'content', 'summary',
                          'category', 'file_path', 'created_at', 'updated_at']
        for post in posts:
            for field in required_fields:
                assert field in post, f"缺少字段: {field}"

    def test_front_matter_parsed(self, sample_md_files, posts_dir):
        """测试 front matter 被正确解析"""
        posts = scan_markdown_folder(posts_dir)
        flask_post = next((p for p in posts if 'Flask' in p['title']), None)
        assert flask_post is not None
        assert flask_post['title'] == 'Flask 入门指南'
        assert flask_post['summary'] == '一篇 Flask 入门教程'

    def test_category_from_folder(self, sample_md_files, posts_dir):
        """测试从文件夹名获取分类"""
        posts = scan_markdown_folder(posts_dir)
        categories = {p['category'] for p in posts}
        assert '技术' in categories
        assert '生活' in categories

    def test_root_folder_category(self, sample_md_files, posts_dir):
        """测试根目录文件的分类"""
        posts = scan_markdown_folder(posts_dir)
        general_post = next((p for p in posts if '通用' in p['title']), None)
        assert general_post is not None
        # 根目录下的文件分类应来自 front matter 或默认为 '未分类'

    def test_scan_empty_folder(self, posts_dir):
        """测试扫描空文件夹"""
        posts = scan_markdown_folder(posts_dir)
        assert posts == []

    def test_scan_nonexistent_folder(self, tmp_path):
        """测试扫描不存在的文件夹"""
        folder = str(tmp_path / 'nonexistent')
        posts = scan_markdown_folder(folder)
        assert posts == []

    def test_ignore_non_markdown_files(self, posts_dir):
        """测试忽略非 Markdown 文件"""
        # 创建一个 .txt 文件
        with open(os.path.join(posts_dir, 'readme.txt'), 'w', encoding='utf-8') as f:
            f.write('这不是 Markdown')
        with open(os.path.join(posts_dir, 'test.md'), 'w', encoding='utf-8') as f:
            f.write('# 这是 Markdown')

        posts = scan_markdown_folder(posts_dir)
        assert len(posts) == 1

    def test_scan_supports_markdown_extension(self, posts_dir):
        """测试支持 .markdown 扩展名"""
        with open(os.path.join(posts_dir, 'test.markdown'), 'w', encoding='utf-8') as f:
            f.write('# Markdown 扩展名')

        posts = scan_markdown_folder(posts_dir)
        assert len(posts) == 1

    def test_posts_sorted_by_date(self, sample_md_files, posts_dir):
        """测试结果按创建时间倒序排列"""
        posts = scan_markdown_folder(posts_dir)
        for i in range(len(posts) - 1):
            assert posts[i]['created_at'] >= posts[i+1]['created_at']


class TestGetCategoriesFromFolder:
    """文件夹分类获取测试"""

    def test_get_categories(self, sample_md_files, posts_dir):
        """测试获取子文件夹名作为分类"""
        cats = get_categories_from_folder(posts_dir)
        assert '技术' in cats
        assert '生活' in cats

    def test_ignore_hidden_folders(self, posts_dir):
        """测试忽略隐藏文件夹"""
        os.makedirs(os.path.join(posts_dir, '.hidden'), exist_ok=True)
        os.makedirs(os.path.join(posts_dir, '技术'), exist_ok=True)

        cats = get_categories_from_folder(posts_dir)
        assert '.hidden' not in cats
        assert '技术' in cats

    def test_empty_folder(self, posts_dir):
        """测试空文件夹返回空列表"""
        cats = get_categories_from_folder(posts_dir)
        assert cats == []

    def test_nonexistent_folder(self, tmp_path):
        """测试不存在的文件夹"""
        cats = get_categories_from_folder(str(tmp_path / 'missing'))
        assert cats == []

    def test_sorted_result(self, posts_dir):
        """测试结果按字母排序"""
        for name in ['项目', '技术', '生活']:
            os.makedirs(os.path.join(posts_dir, name))

        cats = get_categories_from_folder(posts_dir)
        assert cats == sorted(cats)
