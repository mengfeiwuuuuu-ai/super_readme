---
title: Jetson Orin NX 多网卡持久化命名与静态 IP 配置方案
date: 2026-02-15
category: 技术
tags: 工具, 效率, 推荐
summary: 多网卡持久化命名与静态 IP 配置方案
---
# Jetson Orin NX 多网卡持久化命名与静态 IP 配置方案

## 文档控制 (Document Control)

* **作者：** mengfei.wuuuu@gmail.com
* **日期：** 2026-02-25
* **当前版本：** V1.0
* **文档密级：** 内部公开 (Internal)

### 修改记录 (Revision History)

| 版本 (Version) | 修改日期 (Date) | 修改人 (Author) | 修改说明 (Description) |
| --- | --- | --- | --- |
| V1.0 | 2026-02-25 | mengfei.wuuuu@gmail.com | 初始版本发布：确立基于 PCIe 路径的网卡持久化命名规则与多网口 DHCP Netplan 路由优先级策略。 |

---

## 1. 背景与目的

在 Jetson Orin NX 设备（及多网卡载板）的生产与部署过程中，网卡的 MAC 地址可能会发生变化（如：量产烧录前未固化 MAC、更换核心模组或随机 MAC 策略等）。这种变化会导致基于 MAC 地址的网络配置失效，并在系统重启后出现网卡名称（如 `enP...`）乱序漂移的问题。

**本方案的目的：**
放弃传统的 MAC 地址绑定方式，采用基于**硬件物理拓扑（PCIe Path）**的系统级绑定方案。确保无论底层模块如何更换、MAC 地址如何变动，特定的物理网口永远对应固定的系统网卡名称，并自动应用正确的静态 IP 配置。

## 2. 方案概述

本方案采用 Linux 现代网络管理标准，结合以下三个组件实现：

1. **Systemd-networkd (`.link` 文件)**：在系统引导的早期阶段（initramfs），通过匹配网卡的底层 PCIe 总线物理路径，将其强制重命名为指定的名称。
2. **Netplan**：作为高级网络配置前端，统一管理网卡的静态 IP、路由和 DNS。
3. **NetworkManager**：作为底层渲染器执行具体的网络连接，并在实施新方案前清理旧的脏数据（冗余的 Connection Profiles）。

---

## 3. 详细实施步骤

### 3.1 基于 PCIe 物理路径绑定网卡名称

通过新建 Systemd `.link` 文件，将探测到的固定 PCIe 硬件路径（`ID_PATH`）与预期的网络接口名称（Name）进行硬绑定。

1. **配置节点一（绑定为 `enP1p1s0`）**
创建文件：`sudo nano /etc/systemd/network/10-pcie-enP1p1s0.link`
写入以下内容：
```ini
[Match]
Path=platform-140a0000.pcie-pci-0008:01:00.0

[Link]
Name=enP1p1s0

```


2. **配置节点二（绑定为 `enP8p1s0`）**
创建文件：`sudo nano /etc/systemd/network/10-pcie-enP8p1s0.link`
写入以下内容：
```ini
[Match]
Path=platform-14100000.pcie-pci-0001:01:00.0

[Link]
Name=enP8p1s0

```



### 3.2 更新网络配置文件 (Netplan)

修改系统网络配置，为绑定好名称的网口下发静态 IP 策略。

编辑文件：`sudo nano /etc/netplan/01-network-manager-all.yaml`
写入/更新为以下内容：

```yaml
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    enP1p1s0:
      dhcp4: no
      addresses:
        - 192.168.137.100/24
      routes:
        - to: default
          via: 192.168.137.1
      nameservers:
        addresses: [114.114.114.114, 8.8.8.8]

```

*(注：为消除由于权限过高引起的系统警告，建议执行 `sudo chmod 600 /etc/netplan/01-network-manager-all.yaml` 修缮文件权限。)*

### 3.3 更新系统引导镜像 (initramfs)

由于 `.link` 文件的命名规则必须在内核挂载根文件系统之前生效，必须更新 initramfs 镜像以包含上述 `.link` 规则：

```bash
sudo update-initramfs -u

```

*(**关键**：若遗漏此步，系统重启后网卡重命名策略将无法生效。)*

### 3.4 清理冗余 NetworkManager 配置并重启

清理系统中原有的通过 `nmcli` 或图形界面创建的历史连接配置（如名为 `static` 的连接），避免与 Netplan 下发的配置发生冲突。

```bash
# 删除旧有的静态连接节点
sudo nmcli connection delete "static"

# 重启设备以应用全局变更
sudo reboot

```

---

## 4. 验证与排错 (Troubleshooting)

重启设备后，可通过以下指令验证配置是否符合预期：

1. **验证网卡名称与 IP 地址：**
运行 `ifconfig -a` 或 `ip addr`。确认 `enP1p1s0` 是否已成功获取 `192.168.137.100`。
2. **验证物理连接状态 (Carrier)：**
若通过 `ifconfig` 看到对应网卡缺少 `RUNNING` 标志，或通过 `nmcli device status` 看到状态为 `unavailable`，说明物理网线未连接或对端交换机未开启。NetworkManager 默认在无载波（无物理链路）时不会使静态 IP 状态生效，插入网线后即可自动恢复。
3. **验证路由规则：**
运行 `ip route` 检查默认网关（`192.168.137.1`）是否准确指向对应的接口。

---