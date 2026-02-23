---
title: MyBlob 博客系统项目介绍
date: 2026-02-22
category: 项目
tags: 项目, 博客, 开源
summary: MyBlob 是一个基于 Flask 的现代博客系统，支持 Markdown 渲染、多主题切换、GitHub 代理等功能。
---

# MyBlob 博客系统

## 🚀 项目概述

MyBlob 是一个功能完善的个人博客系统，基于 Python Flask 框架构建，旨在为用户提供简洁优雅的博客写作和阅读体验。

## ✨ 核心特性

### 📄 Markdown 支持
- 完整的 Markdown 语法渲染
- 代码高亮显示
- 表格、TOC 目录支持
- 实时预览编辑器

### 🎨 多主题切换
系统内置 5 种精心设计的主题：
- 🌞 **Light** - 清爽明亮的默认主题
- 🌙 **Dark** - 护眼暗黑模式
- 🌊 **Ocean** - 清凉海洋蓝调
- 🌲 **Forest** - 自然森林绿意
- 🌅 **Sunset** - 温暖日落暖色

### 📁 自动 Markdown 文件识别
将 Markdown 文件放入 `posts/` 文件夹即可自动识别：
- 支持子文件夹作为分类
- 支持 Front Matter 元数据
- 自动生成摘要和 slug

### 👥 用户管理
- 注册 / 登录 / 注销
- 管理员权限控制
- 个人资料编辑

### 🐙 GitHub 代理
- 查看 GitHub 仓库信息
- 渲染 README 文档
- 搜索 GitHub 仓库
- 浏览用户公开仓库

## 🛠️ 技术架构

```
myblob/
├── app.py              # 主应用
├── config.py           # 配置文件
├── models/             # 数据模型
├── utils/              # 工具模块
├── templates/          # HTML 模板
├── static/             # 静态资源
└── posts/              # Markdown 文件
```

## 📄 许可证

MIT License - 自由使用、修改和分发。

---

*感谢使用 MyBlob！*
