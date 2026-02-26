---
title: Jetson Orin 扩展网卡 (I350) 持久化命名与 DHCP 配置方案
date: 2026-02-15
category: 技术
tags: 工具, 效率, 推荐
summary: 多网卡持久化命名与静态 IP 配置方案
---
# Jetson Orin 扩展网卡 (I350) 持久化命名与 DHCP 配置方案

## 文档控制 (Document Control)

* **作者：** mengfei.wuuuu@gmail.com
* **日期：** 2026-02-25
* **当前版本：** V1.0
* **文档密级：** 内部公开 (Internal)

### 修改记录 (Revision History)

| 版本 (Version) | 修改日期 (Date) | 修改人 (Author) | 修改说明 (Description) |
| --- | --- | --- | --- |
| V1.0 | 2026-02-25 | mengfei.wuuuu@gmail.com | 初始版本发布：确立基于 PCIe 路径的 I350 网卡持久化命名规则与多网口 DHCP Netplan 路由优先级策略。 |

---

## 1. 背景与目的

在 Jetson Orin 平台上，通过内部 PCIe 总线扩展了 Intel I350 四口千兆网卡。默认情况下，系统内核根据枚举顺序为其分配了如 `enP1p1s0f0` 等动态名称。由于量产更换模组、MAC 地址变更等因素，传统的基于 MAC 地址的网卡识别方式存在绑定失效的隐患。

**本方案的目的：**
基于底层的 PCIe 硬件拓扑路径，将 I350 网卡的四个物理端口（`f0`、`f1`、`f2`、`f3`）分别硬性绑定为标准名称 `eth0`、`eth1`、`eth2` 和 `eth3`，并统一配置为 DHCP 动态获取 IP 模式，从而实现网络行为的稳定一致与即插即用。

## 2. 方案概述

本方案的核心逻辑是通过提取 I350 每个物理网口的固化 `ID_PATH`，利用 Systemd 的链路级配置工具进行重命名，再通过 Netplan 统一接管路由与 IP 寻址：

1. **Systemd `.link**`：在系统引导的早期阶段（initramfs 阶段）截获网卡初始化，依据物理拓扑（Function 0~3）强行分配指定的 `ethX` 名称。
2. **Netplan & NetworkManager**：定义标准化的网络策略，开启全网口的 DHCP4 自动获取功能，并设置路由度量值（Metric）防止多网关冲突。

---

## 3. 详细实施步骤

### 3.1 基于 PCIe 物理路径绑定网卡名称

针对 I350 的 4 个网口，我们需要在 `/etc/systemd/network/` 目录下创建对应的 `.link` 规则文件。

**1. 绑定 eth0 (对应原 enP1p1s0f0)**
创建文件：`sudo nano /etc/systemd/network/10-pcie-eth0.link`
写入内容：

```ini
[Match]
Path=platform-14100000.pcie-pci-0001:01:00.0

[Link]
Name=eth0

```

**2. 绑定 eth1 (对应原 enP1p1s0f1)**
创建文件：`sudo nano /etc/systemd/network/10-pcie-eth1.link`
写入内容：

```ini
[Match]
Path=platform-14100000.pcie-pci-0001:01:00.1

[Link]
Name=eth1

```

**3. 绑定 eth2 (对应原 enP1p1s0f2)**
创建文件：`sudo nano /etc/systemd/network/10-pcie-eth2.link`
写入内容：

```ini
[Match]
Path=platform-14100000.pcie-pci-0001:01:00.2

[Link]
Name=eth2

```

**4. 绑定 eth3 (对应原 enP1p1s0f3)**
创建文件：`sudo nano /etc/systemd/network/10-pcie-eth3.link`
写入内容：

```ini
[Match]
Path=platform-14100000.pcie-pci-0001:01:00.3

[Link]
Name=eth3

```

### 3.2 更新网络配置文件 (Netplan)

修改现有的 Netplan 配置文件，接管这 4 个新命名的网卡，并将其统一配置为 DHCP 模式。

编辑文件：`sudo nano /etc/netplan/01-network-manager-all.yaml`
*(注：如果目标设备文件名称不同，请根据 `/etc/netplan/` 目录下的实际情况调整)*

写入或更新为以下内容（请注意 YAML 格式对空格缩进极其敏感）：

```yaml
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    eth0:
      dhcp4: true
      dhcp4-overrides:
        route-metric: 100
    eth1:
      dhcp4: true
      dhcp4-overrides:
        route-metric: 200
    eth2:
      dhcp4: true
      dhcp4-overrides:
        route-metric: 300
    eth3:
      dhcp4: true
      dhcp4-overrides:
        route-metric: 400

```

> **设计说明：** 为防止 4 个网卡同时连接不同网络时产生默认路由 (Default Gateway) 冲突，此处加入了 `route-metric` 优先级配置。数值越小，路由优先级越高（即系统优先通过 `eth0` 访问外网）。如果仅在局域网内通讯，此参数为非必需，但作为稳健设计建议保留。

**安全合规操作：** 为消除由于文件权限过高引起的系统警告，建议执行以下命令修缮文件权限：

```bash
sudo chmod 600 /etc/netplan/01-network-manager-all.yaml

```

### 3.3 更新系统引导镜像 (initramfs)

由于 `.link` 文件的命名规则必须在内核挂载根文件系统之前生效，必须更新 initramfs 镜像以包含上述 `.link` 规则：

```bash
sudo update-initramfs -u

```

*(**关键**：若遗漏此步，系统重启后网卡重命名策略将无法生效。)*

### 3.4 清理冗余配置并重启

为了避免旧的网卡配置残留（NetworkManager 基于 MAC 记录的历史自动连接）对新网卡产生干扰，执行清理操作后重启系统。

```bash
# 清理 NetworkManager 中原有的所有历史连接配置 (可选但推荐，恢复网络纯净状态)
sudo nmcli --fields UUID connection show | awk 'NR>1 {print $1}' | xargs -r sudo nmcli connection delete

# 重启设备使底层重命名规则及网络配置生效
sudo reboot

```

---

## 4. 验证测试 (Troubleshooting)

系统重启完成后，可通过以下步骤检验配置是否符合预期：

1. **查验网卡名称映射：**
执行 `ifconfig -a` 或 `ip link`。
**预期结果：** 旧的 `enP1p1s0fX` 彻底消失，取而代之的是物理顺序规整的 `eth0`、`eth1`、`eth2`、`eth3`。
2. **查验 DHCP 获取状态：**
将网线插入对应网口，执行 `ip addr`。
**预期结果：** 带有 `RUNNING` 标记（即检测到物理载波）的网卡会自动从上级路由器/交换机获取到动态 IP 地址。
3. **查验 NetworkManager 托管状态：**
执行 `nmcli device status`。
**预期结果：** 网口状态应显示为 `connected`（已连接，若插了网线）或 `unavailable`（不可用，若未插网线），并且明确显示受 `NetworkManager` 正常托管。

---