---
title: Jetson Orin 显示器三色自动测试方案文档
date: 2026-02-15
category: 技术
tags: 工具, 效率, 推荐
summary: 提供一种自动化、高效率的显示器三色（红、绿、蓝）屏幕测试方法
---
# Jetson Orin 显示器三色自动测试方案文档

## 文档信息

* **作者**: mengfei.wuuuu@gmail.com
* **创建日期**: 2026-02-25
* **当前版本**: V1.0
* **适用平台**: NVIDIA Jetson Orin (JetPack 6.2 / L4T 36.4.3 / Kernel 5.15.148)

## 修订记录

| 版本号 | 修订日期 | 修订人 | 修订说明 |
| --- | --- | --- | --- |
| V1.0 | 2026-02-25 | mengfei.wuuuu@gmail.com | 初始版本发布，包含基于 Python3、xrandr 和 GStreamer 的自动化三色测试方案。 |

---

## 1. 方案概述

本方案旨在为基于 NVIDIA Jetson Orin 平台的设备提供一种自动化、高效率的显示器三色（红、绿、蓝）屏幕测试方法。该测试主要用于产线质检或开发阶段的屏幕坏点、色彩渲染及显示通路验证。

方案采用 Python 3 编写控制脚本，结合 X11 系统的 `xrandr` 工具实现物理显示器分辨率的动态获取与自适应，底层调用 GStreamer 原生多媒体框架高效生成纯色视频流，从而实现全屏、无缝的色彩切换测试。

---

## 2. 运行环境配置

本方案已针对以下软硬件环境进行验证，确保兼容性与稳定性：

* **硬件平台**: NVIDIA Jetson Orin
* **操作系统**: Ubuntu 22.04 LTS
* **BSP 版本**: JetPack 6.2 / L4T 36.4.3
* **核心依赖**:
* Python 3.x（系统自带）
* `x11-xserver-utils` (提供 `xrandr` 命令)
* `gstreamer1.0-tools`及相关基础插件 (提供 `gst-launch-1.0` 等命令)



*(注：上述基础工具通常在包含图形界面的 JetPack 固件中已默认预装，无需额外编译安装。)*

---

## 3. 技术实现原理

测试脚本的执行流程分为三个核心步骤：

1. **环境定向 (`export DISPLAY=:0`)**
脚本在初始化时强制将运行环境的 `DISPLAY` 环境变量设置为 `:0`。这确保了即使测试脚本是通过 SSH 远程终端触发的，生成的图像信号也能准确无误地投射到直接与 Jetson 连接的物理显示器上。
2. **动态分辨率探测 (`xrandr`)**
通过 Python 的 `subprocess` 模块调用系统 `xrandr` 命令，并使用正则表达式捕获带有 `*` 标识的当前激活分辨率（如 `1920x1080`）。以此作为后续画面生成的参数，确保纯色画面能够 100% 覆盖不同规格的屏幕，避免出现黑边。
3. **硬件加速渲染 (`GStreamer` 管道)**
利用 `gst-launch-1.0` 构造渲染管道：
* 使用 `videotestsrc pattern=solid-color` 生成纯色源。
* 配合 `foreground-color` 指定十六进制颜色值。
* 经过 Jetson 专用的 `nvvidconv` 插件处理，最后由 `xvimagesink` 将画面推送到 X Server。
* Python 主进程通过 `time.sleep()` 控制单色显示时长，并通过进程管理 (`terminate`) 实现颜色的自动轮换。



---

## 4. 核心代码实现

请在 Jetson 设备上创建文件 `jetson_display_test.py`，并将以下代码完整粘贴：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jetson Orin Display Color Test Script
Platform: JetPack 6.2 / Ubuntu 22.04
Description: Automated Full-screen Red/Green/Blue color test using xrandr and GStreamer.
Author: mengfei.wuuuu@gmail.com
Version: V1.0
Date: 2026-02-25
"""

import os
import sys
import subprocess
import re
import time
import argparse

def setup_environment():
    """配置 DISPLAY 环境变量，确保 SSH 环境下也能正常在物理屏幕输出。"""
    os.environ["DISPLAY"] = ":0"
    print("[Info] Environment variable DISPLAY set to :0")

def get_screen_resolution():
    """通过 xrandr 获取当前激活状态的物理屏幕分辨率。"""
    try:
        cmd = "xrandr"
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        
        # 匹配如 "1920x1080     60.00*+" 中带有星号的当前激活分辨率
        pattern = re.compile(r'(\d+)x(\d+)\s+.*\*')
        match = pattern.search(output)
        
        if match:
            width = match.group(1)
            height = match.group(2)
            print(f"[Info] Detected active screen resolution: {width}x{height}")
            return width, height
        else:
            print("[Warning] Could not parse resolution from xrandr. Defaulting to 1920x1080.")
            return "1920", "1080"
            
    except subprocess.CalledProcessError:
        print("[Error] Failed to execute xrandr. Is the X server running and display connected?")
        sys.exit(1)

def run_gstreamer_color_test(color_name, hex_value, width, height, duration):
    """构建并运行 GStreamer 管道以全屏显示指定纯色。"""
    print(f"--> Rendering {color_name} (Color Code: 0x{hex_value}) for {duration} seconds...")
    
    # GStreamer 渲染管道
    gst_cmd = [
        "gst-launch-1.0",
        "videotestsrc", "pattern=solid-color", f"foreground-color={hex_value}",
        "!", f"video/x-raw,width={width},height={height}",
        "!", "nvvidconv",
        "!", "xvimagesink", "force-aspect-ratio=false"
    ]
    
    # 以后台子进程启动渲染管道
    process = subprocess.Popen(
        gst_cmd, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL
    )
    
    try:
        # 维持画面指定时长
        time.sleep(duration)
    finally:
        # 时长结束，安全终止进程
        process.terminate()
        process.wait()

def main():
    # 命令行参数解析
    parser = argparse.ArgumentParser(description="Jetson AGX Orin RGB Display Test Automation")
    parser.add_argument("-r", "--rounds", type=int, default=1, help="Number of test loops (default: 1)")
    parser.add_argument("-d", "--duration", type=float, default=3.0, help="Duration per color in seconds (default: 3.0)")
    args = parser.parse_args()

    # 初始化设置
    setup_environment()
    width, height = get_screen_resolution()
    
    # 定义测试序列 (名称, GStreamer十六进制颜色码)
    colors = [
        ("RED",   "0xff0000"),
        ("GREEN", "0x00ff00"),
        ("BLUE",  "0x0000ff")
    ]
    
    print(f"\n=== Starting RGB Display Test (Total Rounds: {args.rounds}) ===")
    
    try:
        for i in range(args.rounds):
            print(f"\n--- Test Cycle {i+1}/{args.rounds} ---")
            for color_name, hex_val in colors:
                run_gstreamer_color_test(color_name, hex_val, width, height, args.duration)
                
        print("\n=== Test Completed Successfully ===")
        
    except KeyboardInterrupt:
        print("\n[Warning] Test interrupted manually by user.")

if __name__ == "__main__":
    main()

```

---

## 5. 使用说明

该脚本具备良好的灵活性，可通过终端参数自定义测试行为。在运行前，请确保 Jetson 已连接物理显示器并已进入 Ubuntu 桌面系统。

**基础运行 (默认 1 轮，每种颜色 3 秒):**

```bash
python3 jetson_display_test.py

```

**自定义运行轮数 (如运行 5 轮):**

```bash
python3 jetson_display_test.py --rounds 5

```

或使用简写：

```bash
python3 jetson_display_test.py -r 5

```

**自定义单色停留时间 (如每种颜色停留 1 秒，实现快速闪烁测试):**

```bash
python3 jetson_display_test.py --duration 1.0

```

**组合使用 (运行 10 轮，每色停留 2 秒):**

```bash
python3 jetson_display_test.py -r 10 -d 2

```

---

## 6. 注意事项与异常排查

| 常见现象 | 可能原因 | 解决建议 |
| --- | --- | --- |
| **报错：Failed to execute xrandr** | X Server 未启动或物理显示器未连接。 | 检查 HDMI/DP 线缆是否插紧，确保设备已开机进入了 Ubuntu 图形化登录界面或桌面。 |
| **画面没有输出到屏幕** | 当前用户权限不足或多用户登录冲突。 | 尝试在连接了物理屏幕的本地键盘上打开终端运行；若是 SSH 登录，确保所使用的账号与设备本地登录的账号一致。 |
| **GStreamer 抛出 pipeline 错误** | 缺少必要的 GStreamer 插件 (`xvimagesink`)。 | 运行 `sudo apt-get install gstreamer1.0-x` 或 `sudo apt-get install gstreamer1.0-plugins-base` 补全基础插件。 |
| **画面四周有黑边** | `xrandr` 抓取到了非原生比例的分辨率。 | 手动将系统显示设置中的分辨率调整为显示器推荐的物理分辨率。 |

---