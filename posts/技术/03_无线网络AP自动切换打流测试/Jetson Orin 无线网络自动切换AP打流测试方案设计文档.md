---
title: Jetson Orin 无线网络自动切换AP打流测试方案设计文档
date: 2026-02-15
category: 技术
tags: 工具, 效率, 推荐
summary: 无线网络自动切换AP打流测试
---
# Jetson Orin 无线网络自动切换AP打流测试方案设计文档

**文档基本信息**

* **文档版本**: V1.0
* **编写日期**: 2026-02-25
* **作 者**: mengfei.wuuuu@gmail.com

## 修改记录

| 版本 | 修改日期 | 修改人 | 修改描述 |
| :--- | :--- | :--- | :--- |
| V1.0 | 2026-02-24 | mengfei.wuuuu@gmail.com | 初始版本创建。 |
| V1.1 | 2026-02-24 | mengfei.wuuuu@gmail.com | 实现基于 `nmcli` 的热点自动连接。 |
| V1.2 | 2026-02-24 | mengfei.wuuuu@gmail.com | 集成外部 `equip.py` 打流脚本及状态码校验。 |
| V1.3 | 2026-02-24 | mengfei.wuuuu@gmail.com | 新增详细日志与 CSV 统计双重输出机制。 |
| V2.0 | 2026-02-25| mengfei.wuuuu@gmail.com | 增加命令行限时运行 (`--duration`) 控制功能。 |
---

## 1. 需求背景与概述

在 Jetson Orin 平台上，针对设备的无线网络（Wi-Fi）连通性与吞吐量（打流）需要进行长时间的自动化压力测试。本方案旨在提供一个基于 Python 3 的自动化脚本工具，通过控制系统底层的 `NetworkManager` 模块与外部打流测试脚本（`equip.py`）进行联动，实现“自动连接热点 -> 执行吞吐量测试 -> 记录测试数据 -> 循环/限时运行”的完整自动化闭环，极大地降低人工干预成本并提供可靠的测试数据记录。

## 2. 运行环境配置

本方案针对特定的软硬件环境设计，依赖以下系统配置：

* **硬件平台**: NVIDIA Jetson Orin
* **操作系统**: Ubuntu 22.04 LTS
* **系统版本**: Jetpack 6.2 / L4T 36.4.3
* **内核版本**: 5.15.148
* **网络管理**: `NetworkManager` (nmcli)
* **运行语言**: Python 3.x
* **外部依赖**: 预置的打流测试框架 (`/home/cnit/.venv/bin/python equip.py`)

## 3. 核心功能特性

* **自动化网络控制**: 通过 `nmcli` 指令静默扫描并连接无密码 Wi-Fi 热点（如 "ROBOT"）。
* **进程状态监控**: 使用子进程（`subprocess`）调用外部测试脚本，实时捕获标准输出与标准错误，并精确捕捉退出状态码以判定测试成功与否。
* **双重日志系统**:
* **全量日志 (`.log`)**: 完整记录系统调度信息及外部测试工具的原始控制台输出，包含吞吐量、连通性等详细回显。
* **结构化统计 (`.csv`)**: 提炼每次测试的起始时间、结束时间、单次耗时及最终 Pass/Fail 结果，方便导入 Excel 进行图表分析。


* **灵活的运行模式**: 支持无限循环压力测试，以及通过命令行参数指定运行时间（如运行 12.5 小时后自动优雅退出）。
* **故障自恢复**: 网络连接失败或测试异常中断时，具备冷却重试机制，防止程序死锁。

## 4. 架构与逻辑设计

本方案采用面向对象设计，核心逻辑封装在 `WifiTestManager` 与 `Logger` 两个类中：

1. **`Logger` 模块**: 采用类似 `tee` 命令的机制，重写了 `sys.stdout`，使所有 `print()` 与子进程的输出流同时推送到终端屏幕和本地日志文件。
2. **`WifiTestManager` 模块**: 负责调度测试生命周期。
* **前置校验**: 检查是否达到用户设定的超时阈值。
* **网络重置**: 强制扫描并连接目标 SSID，提供 5 秒网络稳定缓冲期。
* **测试执行**: 切换至指定工作目录，拉起虚拟环境中的打流脚本，流式读取输出。
* **数据落地**: 测试结束后，统计耗时与状态，写入 CSV，冷却 5 秒后进入下一轮。



## 5. 完整源代码

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jetson Orin Wi-Fi Automated Throughput Testing Tool
Author: mengfei.wuuuu@gmail.com
Date: 2026-02-25
Version: 1.0
"""

import subprocess
import time
import sys
import os
import datetime
import csv
import argparse

# ================= 核心配置项 =================
TARGET_SSID = "ROBOT"
WIFI_INTERFACE = "wlan0"
WORK_DIR = "/home/cnit/equip_test/equip_test"
TEST_CMD = "sudo /home/cnit/.venv/bin/python equip.py wifi --min_rate 150 --bidir true --repeat 1 --parallel true"

LOG_FILE = "wifi_test_detail.log"  
CSV_FILE = "wifi_test_history.csv" 
# ===========================================

class Logger:
    """双流日志记录器（控制台 + 文件）"""
    def __init__(self, filename):
        self.filename = filename
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()
        
    def close(self):
        self.log.close()

def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def write_csv_record(start_time, end_time, duration, result):
    """写入 CSV 统计记录"""
    file_exists = os.path.isfile(CSV_FILE)
    try:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Start Time', 'End Time', 'Duration(s)', 'Result'])
            writer.writerow([start_time, end_time, f"{duration:.2f}", result])
    except Exception as e:
        print(f"写入CSV失败: {e}")

class WifiTestManager:
    """测试调度管理类"""
    def __init__(self, duration_hours=0):
        self.success_count = 0
        self.fail_count = 0
        self.total_count = 0
        
        self.limit_seconds = duration_hours * 3600
        self.script_start_time = time.time()
        
        # 初始化日志双写
        self.logger = Logger(LOG_FILE)
        sys.stdout = self.logger
        sys.stderr = self.logger

    def log_info(self, msg):
        print(f"[{get_timestamp()}] [System] {msg}")

    def check_time_limit(self):
        """运行时间校验限制"""
        if self.limit_seconds <= 0:
            return False 
            
        elapsed = time.time() - self.script_start_time
        if elapsed >= self.limit_seconds:
            self.log_info(f"已达到预设运行时间: {elapsed/3600:.2f} 小时。")
            return True
        return False

    def connect_wifi(self):
        """通过 nmcli 恢复初始网络连接"""
        self.log_info(f"正在扫描并连接 Wi-Fi: {TARGET_SSID} ...")
        subprocess.run(f"sudo nmcli device wifi rescan ifname {WIFI_INTERFACE}", shell=True, stderr=subprocess.DEVNULL)
        time.sleep(2) 

        cmd = f'sudo nmcli dev wifi connect "{TARGET_SSID}"'
        try:
            result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.log_info(f"成功连接热点: {TARGET_SSID}")
            return True
        except subprocess.CalledProcessError as e:
            self.log_info(f"连接失败: {e.stderr.strip()}")
            return False

    def run_test_script(self):
        """执行打流并实时流式捕获日志"""
        self.log_info(f"准备执行测试命令...")
        start_dt = datetime.datetime.now()
        full_cmd = f"cd {WORK_DIR} && {TEST_CMD}"
        
        test_success = False
        try:
            process = subprocess.Popen(
                full_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
            )
            # 实时读取输出
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    print(line, end='') 

            if process.poll() == 0:
                self.log_info("测试脚本执行完毕: SUCCESS")
                test_success = True
            else:
                self.log_info(f"测试脚本执行异常: FAIL (Code: {process.poll()})")
                test_success = False
        except Exception as e:
            self.log_info(f"执行异常: {e}")
            test_success = False

        # 统计数据落地
        end_dt = datetime.datetime.now()
        duration = (end_dt - start_dt).total_seconds()
        
        self.total_count += 1
        if test_success:
            self.success_count += 1
        else:
            self.fail_count += 1

        write_csv_record(start_dt.strftime("%Y-%m-%d %H:%M:%S"), 
                         end_dt.strftime("%Y-%m-%d %H:%M:%S"), 
                         duration, "PASS" if test_success else "FAIL")
        
        self.log_info(f"当前统计 -> 总次: {self.total_count}, 成功: {self.success_count}, 失败: {self.fail_count}")
        return test_success

    def main_loop(self):
        """测试主循环逻辑"""
        self.log_info("=== 自动化测试程序启动 ===")
        self.log_info(f"模式: {'无限循环' if self.limit_seconds <= 0 else f'限时 {self.limit_seconds/3600:.2f} 小时'}")
            
        try:
            while True:
                if self.check_time_limit():
                    self.log_info("测试时间结束，正常退出循环。")
                    break

                self.log_info(f"--- 开始第 {self.total_count + 1} 轮测试 ---")

                if self.connect_wifi():
                    self.log_info("等待 5 秒稳定网络...")
                    time.sleep(5)
                    self.run_test_script()
                    self.log_info("本轮结束，冷却 5 秒...")
                    time.sleep(5)
                else:
                    self.log_info("WIFI连接失败，等待 5 秒后重试...")
                    time.sleep(5)

        except KeyboardInterrupt:
            self.log_info("\n用户手动停止程序 (Ctrl+C)")
        finally:
            self.log_info("=== 最终测试报告 ===")
            self.log_info(f"总运行时间: {(time.time() - self.script_start_time):.2f} 秒")
            self.log_info(f"总执行次数: {self.total_count} | 成功: {self.success_count} | 失败: {self.fail_count}")
            if self.total_count > 0:
                self.log_info(f"整体成功率: {(self.success_count / self.total_count) * 100:.2f}%")
            
            sys.stdout = self.logger.terminal
            sys.stderr = self.logger.terminal
            self.logger.close()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("错误: 本工具涉及网络接口管理，请务必使用 sudo 权限运行。")
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Jetson Orin Wi-Fi Auto Test Tool')
    parser.add_argument('--duration', type=float, default=0, help='指定运行小时数 (默认 0 表示无限循环)')
    args = parser.parse_args()

    manager = WifiTestManager(duration_hours=args.duration)
    manager.main_loop()

```

## 6. 部署与使用指南

**1. 部署脚本**
将上述代码保存为 `auto_wifi_test.py` 并放置于 Jetson 板卡的任意目录。

**2. 权限说明**
因为脚本需要操作 `NetworkManager`，**必须以 Root (sudo) 权限运行**。

**3. 运行指令示例**

* **模式 A：无限时疲劳测试** (手动按 `Ctrl+C` 结束时会打印统计报告)
```bash
sudo python3 auto_wifi_test.py

```


* **模式 B：指定运行时长** (例如下班前设定运行 12 小时)
```bash
sudo python3 auto_wifi_test.py --duration 12

```


* **模式 C：指定半小时测试** (支持浮点数输入)
```bash
sudo python3 auto_wifi_test.py --duration 0.5

```



## 7. 日志与数据输出说明

每次运行脚本时，将在脚本**当前所处目录**下实时追加生成以下两个核心文件：

1. **`wifi_test_detail.log`**: 完整过程日志。内容涵盖框架调度日志（带有 `[System]` 标签）以及您原有的打流脚本表格报告输出。
2. **`wifi_test_history.csv`**: 历史统计台账。可直接使用表格软件打开，数据结构如下：

| Start Time | End Time | Duration(s) | Result |
| --- | --- | --- | --- |
| 2026-02-25 12:40:03 | 2026-02-25 12:41:06 | 63.00 | PASS |
| 2026-02-25 12:41:15 | 2026-02-25 12:42:18 | 63.00 | FAIL |

---