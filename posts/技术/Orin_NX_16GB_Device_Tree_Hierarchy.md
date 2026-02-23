---
title: 设备树层级调用关系-ORIN NX
date: 2026-02-15
category: 技术
tags: 工具, 效率, 推荐
summary: 开发中总结信息，帮助提升开发体验和工作效率。 
---
# Orin NX 16GB (P3767-0000) 设备树层级关系

> JetPack 6.x | L4T 36.x | 适用于 Orin Nano 开发者套件载板 (P3768)

## 层级结构图

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    最终 DTB (编译目标)                                    │
│     tegra234-p3768-0000+p3767-0000-nv.dtb                               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Level 1: 组合层 (顶层 DTS)                                               │
│ 文件: tegra234-p3768-0000+p3767-0000-nv.dts                             │
│ 路径: source/hardware/nvidia/t23x/nv-public/nv-platform/                │
│ 作用: 组合模组+载板，添加 NV 特定配置 (Power, Thermal, etc.)               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌───────────────────┐  ┌────────────────────┐  ┌──────────────────────┐
│ Level 2: 组合层    │  │ Level 2: 公共层     │  │ Level 2: 模组层       │
│ P3767+P3768 组合   │  │ NV 通用配置         │  │ 16GB SKU 专用定义     │
│                   │  │                    │  │                      │
│ tegra234-p3768    │  │ tegra234-p3768     │  │ tegra234-p3767       │
│ -0000+p3767-0000  │  │ -0000+p3767-xxxx   │  │ -0000.dtsi           │
│ .dts              │  │ -nv-common.dtsi    │  │                      │
└───────────────────┘  └────────────────────┘  └──────────────────────┘
        │                      │                          │
        │                      │                          │
        ▼                      ▼                          ▼
┌───────────────────┐  ┌────────────────────┐  ┌──────────────────────┐
│ Level 3: 载板层    │  │ Level 3: 载板平台层  │  │ Level 3: 模组系列层   │
│ P3768 载板定义     │  │ 载板通用覆盖        │  │ Orin NX 系列公共定义  │
│                   │  │                    │  │                      │
│ tegra234-p3768    │  │ tegra234-p3768     │  │ tegra234-p3767.dtsi  │
│ -0000.dtsi        │  │ -0000.dtsi         │  │                      │
│                   │  │ (nv-platform)      │  │                      │
│ • M.2 Key M/E     │  │                    │  │ • 核心电压轨         │
│ • DisplayPort     │  │                    │  │ • EMC (内存)         │
│ • USB 接口        │  │                    │  │ • 模组 EEPROM        │
│ • 风扇 PWM        │  │                    │  │ • QSPI Flash         │
└───────────────────┘  └────────────────────┘  └──────────────────────┘
        │                                                 │
        └─────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Level 4: SoC 层 (芯片级定义)                                             │
│ 文件: tegra234.dtsi                                                     │
│ 路径: source/kernel/kernel-jammy-src/arch/arm64/boot/dts/nvidia/        │
│ 作用: 定义 Tegra234 SoC 所有硬件外设                                      │
│   • CPU/GIC 中断控制器                                                   │
│   • 所有 I2C/SPI/UART 控制器                                             │
│   • PCIe/USB/以太网控制器                                                │
│   • 时钟/电源/复位                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## 文件位置汇总表

| 层级 | 文件名 | 路径 (相对 `hardware/nvidia/t23x/nv-public/`) | 修改场景 |
|------|--------|------|----------|
| **编译入口** | `tegra234-p3768-0000+p3767-0000-nv.dts` | `nv-platform/` | 添加自定义顶层配置 |
| **组合层** | `tegra234-p3768-0000+p3767-0000.dts` | `./` | 定义模组与载板的连接关系 |
| **通用层** | `tegra234-p3768-0000+p3767-xxxx-nv-common.dtsi` | `nv-platform/` | Orin NX 在 P3768 上的通用配置 |
| **载板层** | `tegra234-p3768-0000.dtsi` | `./` | **修改载板外设** (接口, PCIe, 风扇) |
| **模组层** | `tegra234-p3767-0000.dtsi` | `nv-platform/` | **修改模组配置** (16GB 内存, SKU 电源) |
| **模组系列** | `tegra234-p3767.dtsi` | `./` | 修改 Orin NX 系列公共配置 (SOM 内部) |

## 完整文件路径

```text
Linux_for_Tegra/
├── source/
│   ├── kernel/kernel-jammy-src/arch/arm64/boot/dts/nvidia/
│   │   └── tegra234.dtsi                              # SoC 基础定义
│   │
│   └── hardware/nvidia/t23x/nv-public/
│       ├── tegra234-p3767.dtsi                        # 模组系列 (Orin NX Common)
│       ├── tegra234-p3768-0000.dtsi                   # 载板层 (Orin Nano DevKit Carrier)
│       ├── tegra234-p3768-0000+p3767-0000.dts         # 组合层
│       │
│       ├── nv-platform/
│       │   ├── tegra234-p3768-0000+p3767-0000-nv.dts  # 最终编译入口 (Target)
│       │   ├── tegra234-p3768-0000+p3767-xxxx-nv-common.dtsi # 通用配置
│       │   ├── tegra234-p3767-0000.dtsi               # 模组层 (16GB SKU)
│       │   └── tegra234-p3768-0000.dtsi               # 载板平台层 (Platform Override)
│       │
│       └── nv-soc/                                    # SoC 功能扩展
│           ├── tegra234-soc-overlay.dtsi
│           ├── tegra234-soc-thermal.dtsi
│           └── tegra234-soc-camera.dtsi
```

## 常见修改建议

| 需求 | 修改文件 | 说明 |
|------|----------|------|
| **修改 40-pin 扩展接口** | `tegra234-p3768-0000.dtsi` (根目录那个) | 载板层定义了 GPIO 扩展接口 |
| **修改 PCIe 控制器模式** | `tegra234-p3768-0000+p3767-xxxx-nv-common.dtsi` | 定义 PCIe 根端口配置 |
| **修改风扇控制 (PWM)** | `tegra234-p3768-0000.dtsi` | 载板上的风扇连接定义 |
| **修改 USB 端口映射** | `tegra234-p3768-0000.dtsi` | 定义 USB 物理端口与控制器的对应关系 |
| **修改模组电压/功耗** | `tegra234-p3767-0000.dtsi` | 针对 16GB 模组的具体电源配置 |
| **添加摄像头 (CSI)** | 推荐使用 Overlay DTBO | 避免直接修改核心设备树，使用 `tegra234-p3768-camera-*.dtbo` |

## 设备树编译流程

### 1. 完整编译 (推荐)
使用 NVIDIA 提供的构建脚本：

```bash
# 1. 设置交叉编译工具链 (如果未设置)
export CROSS_COMPILE=/path/to/toolchain/aarch64-linux-gnu-

# 2. 进入源码目录
cd Linux_for_Tegra/source

# 3. 编译内核和设备树
./nvbuild.sh -o $PWD/kernel_out
```

### 2. 仅编译设备树 (快速)
如果只修改了设备树，可以手动调用 `make dtbs`：

```bash
# 假设已在 source 目录
export KERNEL_OUT_DIR=$PWD/kernel_out
make -C kernel/kernel-jammy-src ARCH=arm64 O=$KERNEL_OUT_DIR dtbs
```

### 3. 更新设备树
将生成的 DTB 文件复制到主机上的 L4T 目录准备刷写：

```bash
cp $KERNEL_OUT_DIR/arch/arm64/boot/dts/nvidia/tegra234-p3768-0000+p3767-0000-nv.dtb \
   Linux_for_Tegra/kernel/dtb/
```

然后使用 flash 命令更新设备树分区：
```bash
sudo ./flash.sh -k kernel-dtb jetson-orin-nano-devkit mmcblk0p1
```

## Overlay DTBO 机制

Orin NX/Nano 支持在启动引导阶段 (UEFI/CBoot) 动态加载设备树覆盖 (Overlay)。这允许在不重新编译主设备树的情况下更改硬件配置（如摄像头、显示器）。

### 启用 Overlay
1. 编译你的 `.dts` 为 `.dtbo`：
   ```bash
   dtc -@ -O dtb -o my-overlay.dtbo my-overlay.dts
   ```
2. 将 `.dtbo` 文件放置在设备的 `/boot/` 目录下。
3. 修改 `/boot/extlinux/extlinux.conf`，添加 `fdtoverlays` 条目：
   ```text
   LABEL primary
      MENU LABEL primary kernel
      LINUX /boot/Image
      FDT /boot/dtb/kernel_tegra234-p3768-0000+p3767-0000-nv.dtb
      FDTOVERLAYS /boot/my-overlay.dtbo
      ...
   ```

### 常见官方 Overlay
位于 `Linux_for_Tegra/bootloader/` 或设备 `/boot/` 目录下：
*   `L4TConfiguration.dtbo`: 基础启动配置
*   `tegra234-p3768-0000+p3767-0000-dynamic.dtbo`: 动态调整配置
*   `tegra-optee.dtbo`: 安全环境配置
