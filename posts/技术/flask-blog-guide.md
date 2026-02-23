---
title: Python Flask 博客系统搭建指南
date: 2026-02-20
category: 技术
tags: python, flask, web
summary: 使用 Python Flask 框架从零搭建一个功能完整的博客系统，支持 Markdown、分类管理、主题切换等功能。
---

# Python Flask 博客系统搭建指南

## 简介

Flask 是一个轻量级的 Python Web 框架，非常适合搭建个人博客系统。本文将介绍如何使用 Flask 构建一个功能丰富的博客。

## 技术栈

| 技术 | 用途 |
|------|------|
| Flask | Web 框架 |
| SQLAlchemy | 数据库 ORM |
| Flask-Login | 用户认证 |
| Markdown | 内容渲染 |
| SQLite | 数据存储 |

## 核心功能

### 1. Markdown 支持

博客系统支持完整的 Markdown 语法：

```python
import markdown

md = markdown.Markdown(extensions=[
    'fenced_code',
    'codehilite',
    'tables',
    'toc'
])

html = md.convert(markdown_text)
```

### 2. 分类管理

文章可以归类到多个分类中，支持：
- 创建/删除分类
- 自定义分类图标和颜色
- 按分类筛选文章

### 3. 主题切换

系统内置 5 种精美主题：
1. **Light** - 清新明亮
2. **Dark** - 暗黑模式
3. **Ocean** - 海洋蓝调
4. **Forest** - 森林绿意
5. **Sunset** - 日落暖色

### 4. 自动识别 Markdown 文件

将 `.md` 文件放入 `posts/` 文件夹，系统会自动识别并展示。

## 总结

> Flask 框架简洁而强大，非常适合个人博客项目的开发。结合 Markdown 渲染和丰富的扩展，可以轻松打造出功能完善的博客系统。

---

*本文由 MyBlob 博客系统自动导入*
