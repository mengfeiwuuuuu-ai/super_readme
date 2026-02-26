#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jetson Orin Wi-Fi Automated Throughput Testing Tool
Author: mengfei.wuuuuu@gmail.com
Date: 2026-02-24
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