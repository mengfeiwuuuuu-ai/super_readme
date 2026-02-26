## 文档控制 (Document Control)

* **作者：** mengfei.wuuuu@gmail.com
* **日期：** 2026-02-25
* **当前版本：** V1.0
* **文档密级：** 内部公开 (Internal)

### 修改记录 (Revision History)

| 版本 (Version) | 修改日期 (Date) | 修改人 (Author) | 修改说明 (Description) |
| --- | --- | --- | --- |
| V1.0 | 2026-02-25 | mengfei.wuuuu | 初始版本发布：Orin烧录NVMe时API调用关系 |
---
# Jetson Orin NVMe 烧录 API 调用关系完整梳理

## 命令示例
```bash
sudo ./tools/kernel_flash/l4t_initrd_flash.sh --external-device nvme0n1p1 \
  -c tools/kernel_flash/flash_l4t_t234_nvme.xml \
  --showlogs --network usb0 jetson-agx-orin-devkit external
```

## API 调用层级图

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户命令入口                                        │
│                   l4t_initrd_flash.sh (主脚本)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│ l4t_initrd_flash  │    │ l4t_network_flash │    │ l4t_kernel_flash  │
│ .func             │    │ .func             │    │ _vars.func        │
│ (参数解析)         │    │ (网络配置)         │    │ (变量定义)         │
└───────────────────┘    └───────────────────┘    └───────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     l4t_initrd_flash_internal.sh                            │
│                          (核心烧录逻辑)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ├──▶ l4t_create_images_for_kernel_flash.sh  (生成镜像)
        │           │
        │           └──▶ flash.sh --no-flash  (生成QSPI镜像)
        │                    │
        │                    └──▶ tegraflash.py  (Python底层工具)
        │
        ├──▶ generate_flash_initrd()  (生成Initrd镜像)
        │           │
        │           └──▶ mkbootimg  (打包boot.img)
        │
        ├──▶ boot_initrd()  (启动Initrd)
        │           │
        │           └──▶ tegraflash.py --rcm-boot  (RCM启动)
        │
        └──▶ flash_through_ssh()  (SSH烧录)
                    │
                    └──▶ l4t_flash_from_kernel.sh  (Target端执行)
                                │
                                ├──▶ create_gpt()  (创建GPT分区)
                                ├──▶ flash_extdev()  (烧录NVMe)
                                └──▶ flash_qspi()  (烧录QSPI)
```

## 详细调用链

### Phase 1: 镜像生成阶段 (Host)

| 步骤 | 脚本/函数 | 文件 | 核心操作 |
|------|-----------|------|----------|
| 1.1 | `generate_flash_package()` | l4t_initrd_flash_internal.sh:113 | 组装生成命令 |
| 1.2 | `l4t_create_images_for_kernel_flash.sh` | tools/kernel_flash/ | 生成所有镜像 |
| 1.3 | `generate_signed_images()` | l4t_create_images_for_kernel_flash.sh | 调用flash.sh |
| 1.4 | `flash.sh --no-flash` | flash.sh | 生成QSPI镜像 |
| 1.5 | `tegraflash.py` | bootloader/tegraflash.py | Python底层工具 |

### Phase 2: Initrd 生成阶段 (Host)

| 步骤 | 脚本/函数 | 文件 | 核心操作 |
|------|-----------|------|----------|
| 2.1 | `generate_rcm_bootcmd()` | l4t_initrd_flash_internal.sh:233 | 生成RCM命令 |
| 2.2 | `generate_flash_initrd()` | l4t_initrd_flash_internal.sh:382 | 构建Initrd |
| 2.3 | `abootimg -x` | 外部工具 | 解压recovery.img |
| 2.4 | `mkbootimg` | bootloader/mkbootimg | 打包boot.img |
| 2.5 | `sign_bootimg()` | l4t_initrd_flash_internal.sh:491 | 签名镜像 |

### Phase 3: RCM 启动阶段 (Host → Target)

| 步骤 | 脚本/函数 | 文件 | 核心操作 |
|------|-----------|------|----------|
| 3.1 | `build_working_dir()` | l4t_initrd_flash_internal.sh:210 | 构建工作目录 |
| 3.2 | `copy_bootloader()` | l4t_initrd_flash_internal.sh:644 | 复制bootloader |
| 3.3 | `boot_initrd()` | l4t_initrd_flash_internal.sh:622 | 启动Initrd |
| 3.4 | `tegraflash.py --rcm-boot` | bootloader/ | USB下载模式 |

### Phase 4: 网络通信建立 (Host ↔ Target)

| 步骤 | 脚本/函数 | 文件 | 核心操作 |
|------|-----------|------|----------|
| 4.1 | `network_export()` | l4t_network_flash.func:92 | NFS导出 |
| 4.2 | `enable_nfs_for_folder()` | l4t_network_flash.func:163 | 配置NFS |
| 4.3 | `wait_for_booting()` | l4t_initrd_flash_internal.sh:527 | 等待启动 |
| 4.4 | `wait_for_ssh()` | l4t_initrd_flash_internal.sh:568 | 等待SSH |
| 4.5 | `ping_device()` | l4t_initrd_flash_internal.sh:310 | IPv6通信 |

### Phase 5: 远程烧录阶段 (Host → Target via SSH)

| 步骤 | 脚本/函数 | 文件 | 核心操作 |
|------|-----------|------|----------|
| 5.1 | `flash_through_ssh()` | l4t_network_flash.func:274 | SSH入口 |
| 5.2 | `run_flash_commmand_on_target()` | l4t_network_flash.func:202 | 执行远程命令 |
| 5.3 | `l4t_flash_from_kernel.sh` | images/ | **Target端核心脚本** |

### Phase 6: Target 端烧录执行

| 步骤 | 函数 | 文件:行号 | 操作 |
|------|------|-----------|------|
| 6.1 | `create_gpt_emmc()` | l4t_flash_from_kernel.sh:1228 | 创建eMMC GPT |
| 6.2 | `create_gpt_extdev()` | l4t_flash_from_kernel.sh:1245 | 创建NVMe GPT |
| 6.3 | `flash_qspi()` | l4t_flash_from_kernel.sh:1215 | 烧录QSPI |
| 6.4 | `flash_extdev()` | l4t_flash_from_kernel.sh:1271 | 烧录NVMe |
| 6.5 | `flash_emmc()` | l4t_flash_from_kernel.sh:1257 | 烧录eMMC |

## 关键数据流

```text
flash.idx (分区索引)
    │
    ├── internal/flash.idx ──▶ QSPI分区
    │
    └── external/flash.idx ──▶ NVMe分区
            │
            ├── A_kernel (内核)
            ├── A_kernel-dtb (设备树)
            ├── esp (EFI分区)
            └── APP (根文件系统)
```

## 关键 API 函数表

### Host 端

| 函数名 | 文件 | 作用 |
|--------|------|------|
| `parse_param()` | l4t_initrd_flash.func:117 | 解析命令行参数 |
| `generate_flash_package()` | l4t_initrd_flash_internal.sh:113 | 生成烧录包 |
| `generate_flash_initrd()` | l4t_initrd_flash_internal.sh:382 | 生成Initrd |
| `boot_initrd()` | l4t_initrd_flash_internal.sh:622 | RCM启动 |
| `flash_through_ssh()` | l4t_network_flash.func:274 | SSH烧录入口 |

### Target 端

| 函数名 | 文件:行号 | 作用 |
|--------|-----------|------|
| `create_gpt()` | l4t_flash_from_kernel.sh:1002 | 创建GPT分区表 |
| `write_to_storage()` | l4t_flash_from_kernel.sh:1132 | 写入存储设备 |
| `do_write_storage()` | l4t_flash_from_kernel.sh:780 | 执行单分区写入 |
| `do_write_APP()` | l4t_flash_from_kernel.sh:870 | 写入根文件系统 |
| `flash_partition()` | l4t_flash_from_kernel.sh:461 | 分区烧录核心 |
| `write_sparse_image()` | l4t_flash_from_kernel.sh:703 | 稀疏镜像写入 |
| `write_zstd_image()` | l4t_flash_from_kernel.sh:732 | Zstd镜像写入 |

## 底层工具调用链

```text
l4t_initrd_flash.sh
    │
    └──▶ flash.sh
            │
            └──▶ tegraflash.py
                    │
                    ├──▶ tegrarcm_v2      (RCM通信)
                    ├──▶ tegrahost_v2     (签名)
                    ├──▶ tegrabct_v2      (BCT生成)
                    └──▶ tegradevflash_v2 (刷写)
```

## 网络通信协议

```text
Host                                    Target
  │                                        │
  │──── USB RCM (0955:7023) ──────────────▶│
  │                                        │
  │──── USB RNDIS (IPv6: fc00:1:1::1) ────▶│
  │                                        │
  │◀─── SSH over IPv6 (fe80::1) ───────────│
  │                                        │
  │──── NFS Export ──────────────────────▶│
  │                                        │
  │──── SSH: l4t_flash_from_kernel.sh ────▶│
  │                                        │
```

---
*JetPack 6.2 | L4T 36.4.3 | Kernel 5.15.148*
