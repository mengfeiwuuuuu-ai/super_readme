#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Description: Automated Full-screen Red/Green/Blue color test using xrandr and GStreamer.
Jetson AGX Orin Display Color Test Script
Platform: JetPack 6.2 / Ubuntu 22.04
Author: mengfei.wuuuuu@gmail.com
Date: 2026-02-24
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