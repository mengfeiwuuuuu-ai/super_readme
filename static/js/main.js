/**
 * MyBlob 博客系统 - 前端 JavaScript
 * 主题切换、导航、回到顶部、Flash 消息自动关闭
 */

document.addEventListener('DOMContentLoaded', function () {

    // ==================== 移动端导航切换 ====================
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function () {
            navMenu.classList.toggle('show');
        });

        // 点击其他区域关闭菜单
        document.addEventListener('click', function (e) {
            if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
                navMenu.classList.remove('show');
            }
        });
    }

    // ==================== 主题切换 ====================
    const themeToggle = document.getElementById('themeToggle');
    const themeDropdown = document.getElementById('themeDropdown');

    if (themeToggle && themeDropdown) {
        themeToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            themeDropdown.classList.toggle('show');
        });

        // 点击主题选项
        themeDropdown.querySelectorAll('.theme-option').forEach(function (option) {
            option.addEventListener('click', function () {
                const theme = this.dataset.theme;
                applyTheme(theme);
                themeDropdown.classList.remove('show');

                // 更新选中状态
                themeDropdown.querySelectorAll('.theme-option').forEach(o => o.classList.remove('active'));
                this.classList.add('active');
            });
        });

        // 点击其他区域关闭
        document.addEventListener('click', function (e) {
            if (!themeToggle.contains(e.target) && !themeDropdown.contains(e.target)) {
                themeDropdown.classList.remove('show');
            }
        });
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('myblob-theme', theme);

        // 同步到服务器
        fetch('/api/theme', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ theme: theme })
        }).catch(function () {
            // 静默失败
        });
    }

    // 从 localStorage 恢复主题
    const savedTheme = localStorage.getItem('myblob-theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    }

    // ==================== 回到顶部 ====================
    const backToTop = document.getElementById('backToTop');

    if (backToTop) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 300) {
                backToTop.classList.add('show');
            } else {
                backToTop.classList.remove('show');
            }
        });

        backToTop.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // ==================== Flash 消息自动关闭 ====================
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function (msg) {
        setTimeout(function () {
            msg.style.animation = 'flashOut 0.3s ease forwards';
            setTimeout(function () { msg.remove(); }, 300);
        }, 5000);
    });

    // ==================== 下拉菜单（移动端兼容） ====================
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    dropdownToggles.forEach(function (toggle) {
        toggle.addEventListener('click', function (e) {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                const menu = this.nextElementSibling;
                if (menu && menu.classList.contains('dropdown-menu')) {
                    menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
                }
            }
        });
    });

    // ==================== 图片懒加载增强 ====================
    if ('IntersectionObserver' in window) {
        const imgObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    imgObserver.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(function (img) {
            imgObserver.observe(img);
        });
    }

    // ==================== 代码块复制按钮 ====================
    document.querySelectorAll('.markdown-body pre').forEach(function (pre) {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'code-copy-btn';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = '复制代码';
        copyBtn.style.cssText = 'position:absolute;top:8px;right:8px;background:var(--accent-primary);color:#fff;border:none;border-radius:6px;padding:4px 8px;cursor:pointer;opacity:0;transition:opacity 0.2s;font-size:0.78rem;';

        pre.style.position = 'relative';
        pre.appendChild(copyBtn);

        pre.addEventListener('mouseenter', function () { copyBtn.style.opacity = '1'; });
        pre.addEventListener('mouseleave', function () { copyBtn.style.opacity = '0'; });

        copyBtn.addEventListener('click', function () {
            const code = pre.querySelector('code');
            const text = code ? code.textContent : pre.textContent;
            navigator.clipboard.writeText(text).then(function () {
                copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(function () {
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            });
        });
    });

});

// Flash 消息退出动画
const style = document.createElement('style');
style.textContent = `
    @keyframes flashOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
