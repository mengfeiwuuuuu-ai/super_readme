---
title: Jetson Orin BSP 全栈构建与烧录工具 
date: 2026-02-15
category: 技术
tags: 工具, 效率, 推荐
summary: 支持开发者可以在 Ubuntu 22.04 系统上实现从零开始的交叉编译环境搭建、源码编译、Rootfs 注入以及设备底层烧录
---
# Jetson Orin BSP 全栈构建与烧录工具 (L4T 36.4.3)

## 文档控制 (Document Control)

* **作者**：mengfei.wuuuu@gmail.com
* **日期**：2026-02-25
* **版本**：V2.1
* **状态**：Released
* **文档密级：** 内部公开 (Internal)
* **目标硬件**：NVIDIA Jetson AGX Orin / Orin NX
* **软件基线**：JetPack 6.2 / L4T 36.4.3 (Ubuntu 22.04)

## 修改记录

| 版本 | 修改日期 | 修改人 | 修改描述 |
| :--- | :--- | :--- | :--- |
| V1.0 | 2026-02-24 | mengfei.wuuuu@gmail.com | 初始版本，基于 `build_sdk.sh` 梳理基础编译与烧录流程。 |
| V1.1 | 2026-02-24 | mengfei.wuuuu@gmail.com | 引入 Python3 面向对象重构，封装 `JetsonEnvBuilder` 类进行接口抽象。 |
| V1.2 | 2026-02-24 | mengfei.wuuuu@gmail.com | 实现“代码与产物分离”，将 Day-0 环境构建与 Day-1+ 编译烧录解耦。 |
| V1.3 | 2026-02-24 | mengfei.wuuuu@gmail.com | 修复工具链路径寻址 Bug，完善 `argparse` 命令行组合 SOP 输出。 |
| V2.0 | 2026-02-25| mengfei.wuuuu@gmail.com | 修复 `qemu-user-static` 缺失导致的 `chroot` 异常；修复 GitHub Jekyll 解析 YAML 报错。 |
| V2.1 | 2026-02-25| mengfei.wuuuu@gmail.com | 补充宿主机硬件资源依赖评估；新增 FAQ 异常排查规范；完善系统级可用性约束设计。 |


本项目提供了一套面向 NVIDIA Jetson Orin 家族（AGX Orin, Orin NX）的自动化开发流水线。通过单一整合的 `build_sdk.py` 脚本，开发者可以在 Ubuntu 22.04 系统上实现从零开始的交叉编译环境搭建、源码编译、Rootfs 注入以及设备底层烧录。

## 核心特性

* **一键环境拉起 (Day-0)**：自动检索并解压 `jetpack_env.tar.bz2`，构建标准的 `Linux_for_Tegra` 源码拓扑。
* **模块化编译 (Day-1+)**：支持独立编译 Kernel 镜像、外树模块 (OOT Modules) 以及设备树 (DTBs)。
* **Rootfs 动态注入**：支持将网络配置 (`netplan`)、压测工具 (`gpu_burn` 等)、通讯测试工具 (CAN/RS485) 及开机脚本 (`rc.local`) 根据目标模组类型自动注入到文件系统中。
* **全支持存储介质烧录**：支持将镜像烧录至 NVMe、eMMC (仅限 AGX)、QSPI，并支持 `flash-only` 模式。

---

## 依赖与准备工作

1. **主机系统**：必须为 **Ubuntu 22.04** (宿主机或配置了特权模式的 Docker 容器)。
2. **基础环境包**：确保已获取 NVIDIA 基础支持包 `jetpack_env.tar.bz2`。
* 脚本具有自动寻址能力，建议将该文件提前挂载或拷贝至主机的 `/home`, `/mnt`, `/media` 或 `/opt` 目录下。


3. **特权要求**：本脚本在解压 Rootfs 和烧录设备时需要 Root 权限，执行时请确保当前用户具有 `sudo` 权限。

---

## 目录架构参考

为了保持版本控制的轻量化，本项目采用了**代码与产物分离**的策略。典型的仓库工作区结构如下：

```text
orin-bsp-workspace/
├── build_sdk.py                  # 核心调度脚本
├── README.md                     # 本说明文档
└── nv_tools/                     # 自定义 Rootfs 工具包 (需随 Git 追踪)
    ├── tools_nx/                 # NX 模组专属配置
    └── tools_agx/                # AGX 模组专属配置 (如 nvfancontrol.conf)

```

*(注意：运行 `setup` 后生成的 `workx/` 及 `Linux_for_Tegra/` 目录已被加入 `.gitignore`，请勿将解压产物提交至代码库。)*

---

## 快速上手 (Quick Start)

### 阶段 1：环境初始化 (Day-0)

在一台新的宿主机上，只需执行一次以下命令。它将自动安装交叉编译链依赖 (`build-essential`, `bison`, `flex` 等)，检索 `jetpack_env.tar.bz2`，并完成整个 `~/workx/jetson` 目录树的搭建。

```bash
python3 build_sdk.py setup

```

### 阶段 2：常规编译与构建 (Day-1+)

完成初始化后，你可以使用以下命令进行增量或全量编译。脚本会自动穿透上下文并将交叉编译环境变量挂载就绪。

| 编译指令 | 功能说明 |
| --- | --- |
| `python3 build_sdk.py kernel` | 编译内核镜像 (Kernel Image) |
| `python3 build_sdk.py modules` | 编译外树模块 (OOT Modules) |
| `python3 build_sdk.py dtbs` | 编译设备树 (Device Tree Blobs) |
| `python3 build_sdk.py rootfs nx` | 将 `nv_tools/tools_nx` 注入至 Orin NX 的 Rootfs |
| `python3 build_sdk.py rootfs agx` | 将 `nv_tools/tools_agx` 注入至 AGX Orin 的 Rootfs |
| `python3 build_sdk.py all nx` | **一键全量编译**：执行 kernel + modules + dtbs 并更新 NX 的 Rootfs |

### 阶段 3：固件烧录

使用 Type-C 数据线将 Jetson 设备的 Recovery 接口连接至宿主机，并确保设备处于强制恢复模式 (FC-REC)。

**Orin NX 烧录支持：**

```bash
python3 build_sdk.py flash nx nvme   # 烧录完整系统至 NVMe 固态硬盘
python3 build_sdk.py flash nx qspi   # 仅更新 QSPI 引导程序
python3 build_sdk.py flash nx only   # 执行 flash-only 操作

```

*(注意：Orin NX 不支持 eMMC 烧录)*

**AGX Orin 烧录支持：**

```bash
python3 build_sdk.py flash agx emmc  # 烧录完整系统至内部 eMMC
python3 build_sdk.py flash agx nvme  # 烧录完整系统至外部 NVMe
python3 build_sdk.py flash agx qspi  # 仅更新 QSPI 引导程序
python3 build_sdk.py flash agx only  # 执行 flash-only 操作

```

---

## 自定义组件开发指南

如果你需要为 Rootfs 增加新的自研工具或修改网络配置，**请勿直接修改 `Linux_for_Tegra/rootfs/` 下的文件**。
请将修改落地于当前仓库的 `nv_tools/` 目录中：

1. 将新工具放入对应的 `nv_tools/tools_nx/` 或 `nv_tools/tools_agx/` 目录下。
2. 提交你的修改至 Git。
3. 运行 `python3 build_sdk.py rootfs <module>` 命令，系统会自动利用脚本的注入总线将其覆写至 Rootfs 镜像中。

---