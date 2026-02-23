---
title: 设备树层级调用关系-AGX ORIN
date: 2026-02-15
category: 技术
tags: 工具, 效率, 推荐
summary: 开发中总结信息，帮助提升开发体验和工作效率。 
---
# AGX Orin 64GB (P3701-0000) 设备树层级关系

> JetPack 6.2 | L4T 36.4.3 | Kernel 5.15.148

## 层级结构图

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    最终 DTB (编译目标)                                    │
│     tegra234-p3737-0000+p3701-0000-nv.dtb                               │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Level 1: 组合层 (顶层 DTS)                                               │
│ 文件: tegra234-p3737-0000+p3701-0000-nv.dts                             │
│ 路径: source/hardware/nvidia/t23x/nv-public/nv-platform/                │
│ 作用: 组合模组+载板，添加 NV 特定配置                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌───────────────────┐  ┌────────────────────┐  ┌──────────────────────┐
│ Level 2: 组合层    │  │ Level 2: 公共层     │  │ Level 2: 模组层       │
│ P3737+P3701 组合   │  │ NV 通用配置         │  │ 模组 Overlay          │
│                   │  │                    │  │                      │
│ tegra234-p3737    │  │ tegra234-p3737     │  │ tegra234-p3701       │
│ -0000+p3701-0000  │  │ -0000+p3701-xxxx   │  │ -0000.dtsi           │
│ .dts              │  │ -nv-common.dtsi    │  │                      │
└───────────────────┘  └────────────────────┘  └──────────────────────┘
        │                      │                          │
        │                      │                          │
        ▼                      ▼                          ▼
┌───────────────────┐  ┌────────────────────┐  ┌──────────────────────┐
│ Level 3: 载板层    │  │ Level 3: 公共层     │  │ Level 3: 模组系列层   │
│ P3737 载板定义     │  │ (无)               │  │ P3701 系列公共定义    │
│                   │  │                    │  │                      │
│ tegra234-p3737    │  │                    │  │ tegra234-p3701.dtsi  │
│ -0000.dtsi        │  │                    │  │                      │
│                   │  │                    │  │                      │
│ • RT5640 音频     │  │                    │  │ • I2S/DMIC 使能      │
│ • 风扇            │  │                    │  │ • SD卡/eMMC          │
│ • I2C 外设        │  │                    │  │ • EEPROM             │
│ • 电源调节器      │  │                    │  │ • SPI Flash          │
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
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Level 5: SoC Overlay 层 (功能扩展)                                       │
│ 路径: source/hardware/nvidia/t23x/nv-public/nv-soc/                     │
│ 文件:                                                                   │
│   • tegra234-soc-overlay.dtsi        • tegra234-soc-thermal.dtsi        │
│   • tegra234-soc-prod-overlay.dtsi   • tegra234-soc-camera.dtsi         │
│   • tegra234-soc-audio-dai-links.dtsi                                    │
│ 作用: SoC 级别的功能增强和配置                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## 文件位置汇总表

| 层级 | 文件名 | 路径 | 修改场景 |
|------|--------|------|----------|
| **组合层** | `tegra234-p3737-0000+p3701-0000-nv.dts` | `nv-platform/` | 添加自定义顶层配置 |
| **载板层** | `tegra234-p3737-0000.dtsi` | `t23x/nv-public/` | **修改载板外设** (GPIO, I2C, 风扇) |
| **模组层** | `tegra234-p3701-0000.dtsi` | `t23x/nv-public/` | **修改模组配置** (SD卡, eMMC, SPI) |
| **模组系列** | `tegra234-p3701.dtsi` | `t23x/nv-public/` | 修改 P3701 系列公共配置 |
| **SoC层** | `tegra234.dtsi` | `kernel/.../dts/nvidia/` | 修改 SoC 基础外设定义 |
| **Overlay** | `tegra234-soc-*.dtsi` | `nv-soc/` | 修改特定功能扩展 |

## 完整文件路径

```text
Linux_for_Tegra/
├── source/
│   ├── kernel/kernel-jammy-src/arch/arm64/boot/dts/nvidia/
│   │   └── tegra234.dtsi                          # SoC 基础定义
│   │
│   └── hardware/nvidia/t23x/nv-public/
│       ├── tegra234-p3701-0000.dtsi               # 模组层 (64GB)
│       ├── tegra234-p3701.dtsi                    # 模组系列公共
│       ├── tegra234-p3737-0000.dtsi               # 载板层
│       ├── tegra234-p3737-0000+p3701-0000.dts     # 组合层
│       │
│       ├── nv-platform/
│       │   ├── tegra234-p3737-0000+p3701-0000-nv.dts    # 最终编译入口
│       │   └── tegra234-p3737-0000+p3701-xxxx-nv-common.dtsi
│       │
│       └── nv-soc/
│           ├── tegra234-soc-overlay.dtsi
│           ├── tegra234-soc-prod-overlay.dtsi
│           ├── tegra234-soc-thermal.dtsi
│           ├── tegra234-soc-camera.dtsi
│           └── tegra234-soc-audio-dai-links.dtsi
```

## 常见修改建议

| 需求 | 修改文件 | 说明 |
|------|----------|------|
| 添加/修改 I2C 设备 | `tegra234-p3737-0000.dtsi` | 载板层定义 I2C 外设 |
| 修改 GPIO 引脚 | `tegra234-p3737-0000+p3701-0000.dts` 或 `tegra234-p3737-0000.dtsi` | 根据引脚所属层级 |
| 添加摄像头 | `tegra234-p3737-0000+p3701-xxxx-nv-common.dtsi` 或创建 overlay | 推荐使用 dtbo overlay |
| 修改 SD卡/eMMC | `tegra234-p3701-0000.dtsi` | 模组层定义存储控制器 |
| 添加 PCIe 设备 | `tegra234-p3737-0000+p3701-0000.dts` | 组合层定义 PCIe 配置 |
| 修改 USB 配置 | `tegra234-p3737-0000+p3701-0000.dts` | 组合层定义 USB 端口 |

## 设备树编译流程

```bash
# 1. 进入源码目录
cd Linux_for_Tegra/source

# 2. 编译设备树
./nvbuild.sh -C ../kernel/

# 或者手动编译
cd hardware/nvidia/t23x/nv-public/nv-platform
dtc -@ -I dts -O dtb -o tegra234-p3737-0000+p3701-0000-nv.dtb \
    tegra234-p3737-0000+p3701-0000-nv.dts

# 3. 将生成的 dtb 复制到 bootloader 目录
cp *.dtb ../../../bootloader/
```

## Overlay DTBO 机制

JetPack 6 支持运行时加载设备树覆盖 (Overlay)，推荐用于外设扩展：

```text
bootloader/
├── L4TConfiguration.dtbo           # 基础配置
├── tegra234-p3737-0000+p3701-0000-dynamic.dtbo  # 动态配置
├── tegra234-carveouts.dtbo         # 内存预留
├── tegra-optee.dtbo                # OP-TEE
└── tegra234-p3737-camera-*.dtbo    # 摄像头配置
```

---

*Generated for JetPack 6.2 / L4T 36.4.3*
