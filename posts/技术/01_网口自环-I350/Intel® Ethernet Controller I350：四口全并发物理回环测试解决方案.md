---
title: Intel® Ethernet Controller I350：四口全并发物理回环测试解决方案
date: 2026-02-15
category: 技术
tags: 工具, 效率, 推荐
summary: 实现网口两两自环打流测试
---
# Intel® Ethernet Controller I350：四口全并发物理回环测试解决方案

**文档编号**：INTEL-I350-QUAD-LOOPBACK-V2.1  
**更新日期**：2026-02-12  
**适用硬件**：Intel® I350-T4 / I350-AM4 (四口千兆网卡)  
**主要更新**：新增 NetworkManager 非托管配置，解决 IP 地址自动丢失问题。

---

## 1. 测试拓扑与架构

### 1.1 物理连接 (Physical Setup)

使用两根网线将四个接口两两互连，形成两个独立的物理环路：

* **Group A**: **Port 0** (`enP1p1s0f0`)  **Port 1** (`enP1p1s0f1`)
* **Group B**: **Port 2** (`enP1p1s0f2`)  **Port 3** (`enP1p1s0f3`)

### 1.2 逻辑架构

* **Host (发送端)**: Port 0 & Port 2
* **Namespace (接收端)**: Port 1 & Port 3 (隔离在 `ns_test` 中)

---

## 2. 实施步骤 (SOP)

### 2.1 [关键] 屏蔽 NetworkManager 干扰

**原因**：Linux 桌面版/服务器版默认的 NetworkManager 服务会接管状态为 UP 的网口。在自环（直连）场景下，由于没有 DHCP 服务器，NetworkManager 会在超时（约 45 秒）后判定连接失败并强制清除 IP 地址。

**执行命令**（必须在配置 IP 前执行）：

```bash
# 强制 NetworkManager 停止管理这四个测试网口
nmcli device set enP1p1s0f0 managed no
nmcli device set enP1p1s0f1 managed no
nmcli device set enP1p1s0f2 managed no
nmcli device set enP1p1s0f3 managed no

# 验证状态（应显示为 unmanaged）
nmcli device status | grep enP1p1s0f

```

### 2.2 自动化配置脚本

请将以下内容保存为 `config_i350_loopback.sh` 并以 root 运行。脚本已包含环境清理、命名空间隔离及 IP 配置。

```bash
#!/bin/bash
# Intel I350 Quad-Port Loopback Configuration Script (V2.1)

echo "[1/6] Cleaning up previous configurations..."
pkill iperf3
ip netns del ns_test 2>/dev/null

# 刷新旧 IP
for dev in enP1p1s0f0 enP1p1s0f1 enP1p1s0f2 enP1p1s0f3; do
    ip addr flush dev $dev
    ip link set $dev down
done

echo "[2/6] Setting devices to Unmanaged mode..."
# 防止 IP 自动丢失的关键步骤
nmcli device set enP1p1s0f0 managed no
nmcli device set enP1p1s0f1 managed no
nmcli device set enP1p1s0f2 managed no
nmcli device set enP1p1s0f3 managed no

echo "[3/6] Creating Network Namespace..."
ip netns add ns_test

echo "[4/6] Migrating Receiver Ports (f1, f3) to Namespace..."
# 迁移后主系统将不可见这两个设备
ip link set enP1p1s0f1 netns ns_test
ip link set enP1p1s0f3 netns ns_test

echo "[5/6] Configuring IP Addresses..."

# --- Group A (f0 <-> f1) ---
# Host Side (Sender)
ip link set enP1p1s0f0 up
ip addr add 192.168.10.10/24 dev enP1p1s0f0

# Namespace Side (Receiver)
ip netns exec ns_test ip link set enP1p1s0f1 up
ip netns exec ns_test ip addr add 192.168.10.11/24 dev enP1p1s0f1

# --- Group B (f2 <-> f3) ---
# Host Side (Sender)
ip link set enP1p1s0f2 up
ip addr add 192.168.20.20/24 dev enP1p1s0f2

# Namespace Side (Receiver)
ip netns exec ns_test ip link set enP1p1s0f3 up
ip netns exec ns_test ip addr add 192.168.20.21/24 dev enP1p1s0f3

echo "[6/6] Verifying Connectivity..."
sleep 2 # 等待链路协商
echo "--- Group A Ping (Expect: Success) ---"
ping -c 2 192.168.10.11
echo "--- Group B Ping (Expect: Success) ---"
ping -c 2 192.168.20.21

echo "Configuration Complete. Ready for traffic generation."

```

---

## 3. 双路并发性能测试

### 3.1 启动接收端 (Server)

在 **终端窗口 1** 中运行：

```bash
# 启动 Port 1 接收服务 (Group A)
ip netns exec ns_test iperf3 -s -B 192.168.10.11 -p 5201 &

# 启动 Port 3 接收服务 (Group B)
ip netns exec ns_test iperf3 -s -B 192.168.20.21 -p 5202 &

```

### 3.2 启动发送端 (Client)

在 **终端窗口 2** 中运行：

```bash
# 启动双路打流 (持续 60秒)
iperf3 -c 192.168.10.11 -B 192.168.10.10 -p 5201 -t 60 &
iperf3 -c 192.168.20.21 -B 192.168.20.20 -p 5202 -t 60 &

# 实时监控
watch -n 1 "ethtool -S enP1p1s0f0 | grep packets; echo ''; ethtool -S enP1p1s0f2 | grep packets"

```

---

## 4. 预期结果与还原

### 4.1 性能指标

* **单口带宽**: ~940 Mbps
* **总带宽**: ~1.88 Gbps (双向 x2)
* **稳定性**: 在 60 秒测试周期内，IP 地址应保持稳定，无 `Destination Host Unreachable` 报错。

### 4.2 环境还原

测试结束后，如果希望恢复 NetworkManager 对网口的接管：

```bash
# 1. 删除命名空间
ip netns del ns_test

# 2. 恢复 NetworkManager 托管 (可选)
nmcli device set enP1p1s0f0 managed yes
nmcli device set enP1p1s0f1 managed yes
nmcli device set enP1p1s0f2 managed yes
nmcli device set enP1p1s0f3 managed yes

# 3. 重启网络服务
systemctl restart NetworkManager

```