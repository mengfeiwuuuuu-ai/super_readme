#!/usr/bin/env python3
import os
import subprocess
import sys
import argparse
import time
from datetime import datetime

# ==========================================
# 1. 核心配置与上下文抽象
# ==========================================
class JetsonContext:
    """Jetson Orin L4T 36.4.3 全局路径与状态上下文"""
    def __init__(self, base_work_dir="~/workx/jetson"):
        self.home = os.path.expanduser("~")
        self.work_dir = os.path.expanduser(base_work_dir)
        self.archive_name = "jetpack_env.tar.bz2"
        self.jetpack_archive = os.path.join(self.work_dir, self.archive_name)
        
        # 源码拓扑结构
        self.jetpack_dir = os.path.join(self.work_dir, "jetpack")
        self.orin_dir = os.path.join(self.work_dir, "orin")
        self.tegra_dir = os.path.join(self.orin_dir, "Linux_for_Tegra")
        self.source_dir = os.path.join(self.tegra_dir, "source")
        
        # 交叉工具链
        self.cross_compile_path = os.path.join(self.work_dir, "aarch64--glibc--stable-2022.08-1")
        
        # 版本与状态
        self.l4t_version = "36.4.3"
        self.rootfs_version = "1.00.03"
        self.ver_file = os.path.join(self.tegra_dir, "compile_ver.txt")
        self.log_file = os.path.join(self.tegra_dir, "compile_log.txt")
        self.original_run_dir = os.getcwd() # 记录脚本最初启动的位置

class SystemExecutor:
    """系统命令执行器：隔离底层 OS 调用逻辑"""
    @staticmethod
    def run(cmd: str, cwd: str = None, sudo: bool = False, env: dict = None) -> None:
        if sudo:
            cmd = f"sudo -E {cmd}" if env else f"sudo {cmd}"
        print(f"[*] [{datetime.now().strftime('%H:%M:%S')}] 执行: {cmd}")
        
        result = subprocess.run(cmd, shell=True, cwd=cwd, executable='/bin/bash', env=env)
        if result.returncode != 0:
            sys.exit(f"[!] 命令执行失败 (Exit Code {result.returncode}): {cmd}")

# ==========================================
# 2. 环境构建抽象层 (Day-0)
# ==========================================
class EnvironmentProvisioner:
    """负责系统依赖安装与 BSP 环境拓扑初始化"""
    def __init__(self, ctx: JetsonContext):
        self.ctx = ctx

    def setup_all(self):
        print("\n=== 阶段 1: 基础设施构建 ===")
        self._install_dependencies()
        self._locate_and_prepare_archive()
        self._extract_bsp_and_rootfs()
        self._deploy_tools_and_scripts() # 新增：分发脚本与工具
        
        # 优化：高亮引导开发者进入下一步
        print("\n" + "="*50)
        print("[OK] Jetson Orin L4T 36.4.3 基础环境已彻底就绪！")
        print(f"[*] 构建脚本 `build_sdk.py` 已自动分发至以下目录：")
        print(f"    1. 您的主目录: {self.ctx.home}")
        print(f"    2. L4T源码目录: {self.ctx.tegra_dir}")
        print("="*50)
        print("\n>>> 请直接复制并执行以下命令，进入工作区开始编译：\n")
        print(f"    cd {self.ctx.tegra_dir}")
        print(f"    python3 build_sdk.py all agx\n")

    def _install_dependencies(self):
        SystemExecutor.run("apt update -y", sudo=True)
        deps = "net-tools vim openssh-server tree bison flex git-core build-essential bc libssl-dev libelf-dev qemu-user-static"
        SystemExecutor.run(f"apt install -y {deps}", sudo=True)

    def _locate_and_prepare_archive(self):
        if os.path.exists(self.ctx.jetpack_archive): return
        found = subprocess.run(f"find /home /mnt /media /opt -type f -name '{self.ctx.archive_name}' 2>/dev/null | head -n 1", shell=True, capture_output=True, text=True).stdout.strip()
        if not found: sys.exit(f"[!] 未能找到基础环境包 {self.ctx.archive_name}")
        os.makedirs(self.ctx.work_dir, exist_ok=True)
        SystemExecutor.run(f"cp {found} {self.ctx.jetpack_archive}")

    def _extract_bsp_and_rootfs(self):
        SystemExecutor.run(f"tar -xjf {self.ctx.archive_name}", cwd=self.ctx.work_dir)
        SystemExecutor.run("tar xf aarch64--glibc--stable-2022.08-1.tar.bz2 -C ../", cwd=self.ctx.jetpack_dir)
        
        os.makedirs(self.ctx.orin_dir, exist_ok=True)
        SystemExecutor.run(f"tar xf {self.ctx.jetpack_dir}/Jetson_Linux_R36.4.3_aarch64.tbz2 -C {self.ctx.orin_dir}")
        
        SystemExecutor.run(f"tar xpf {self.ctx.jetpack_dir}/Tegra_Linux_Sample-Root-Filesystem_R36.4.3_aarch64.tbz2 -C {self.ctx.tegra_dir}/rootfs/", sudo=True)
        SystemExecutor.run(f"tar xf {self.ctx.jetpack_dir}/public_sources.tbz2 -C {self.ctx.orin_dir}")
        
        for pkg in ["kernel_src.tbz2", "kernel_oot_modules_src.tbz2", "nvidia_kernel_display_driver_source.tbz2"]:
            SystemExecutor.run(f"tar xf {pkg}", cwd=self.ctx.source_dir)

    def _deploy_tools_and_scripts(self):
        """将当前脚本和必要工具目录分发至目标工作区"""
        current_script = os.path.abspath(__file__)
        nv_tools_dir = os.path.join(self.ctx.original_run_dir, "nv_tools")
        
        # 分发脚本到 ~ 目录
        SystemExecutor.run(f"cp {current_script} {self.ctx.home}/")
        
        # 分发脚本到 Linux_for_Tegra 目录
        SystemExecutor.run(f"cp {current_script} {self.ctx.tegra_dir}/")
        SystemExecutor.run(f"chmod +x {self.ctx.tegra_dir}/build_sdk.py", sudo=True)
        
        # 确保 nv_tools 配置集也被拷贝到 Linux_for_Tegra，供后续 rootfs 注入使用
        if os.path.exists(nv_tools_dir):
            SystemExecutor.run(f"cp -r {nv_tools_dir} {self.ctx.tegra_dir}/")

# ==========================================
# 3. 编译与烧录抽象层 (Day-1+)
# ==========================================
class BuildAndFlashManager:
    """负责核心组件编译、Rootfs 打包及底层设备烧录"""
    def __init__(self, ctx: JetsonContext):
        self.ctx = ctx
        self._validate_env()

    def _validate_env(self):
        if not os.path.exists(self.ctx.tegra_dir):
            sys.exit("[!] L4T 环境尚未初始化，请先运行: python3 build_sdk.py setup")

    def _get_env(self) -> dict:
        env = os.environ.copy()
        env["CROSS_COMPILE_AARCH64_PATH"] = self.ctx.cross_compile_path
        env["CROSS_COMPILE"] = f"{self.ctx.cross_compile_path}/bin/aarch64-buildroot-linux-gnu-"
        env["INSTALL_MOD_PATH"] = os.path.join(self.ctx.tegra_dir, "rootfs/")
        env["IGNORE_PREEMPT_RT_PRESENCE"] = "1"
        env["KERNEL_HEADERS"] = os.path.join(self.ctx.source_dir, "kernel/kernel-jammy-src")
        env["ARCH"] = "arm64"
        return env

    def compile_kernel(self):
        print("\n=== 编译 Kernel ===")
        env = self._get_env()
        SystemExecutor.run('./generic_rt_build.sh "disable"', cwd=self.ctx.source_dir, env=env)
        SystemExecutor.run('make -C kernel', cwd=self.ctx.source_dir, env=env)
        SystemExecutor.run('make install -C kernel', cwd=self.ctx.source_dir, sudo=True, env=env)
        SystemExecutor.run(f"cp {self.ctx.source_dir}/kernel/kernel-jammy-src/arch/arm64/boot/Image {self.ctx.tegra_dir}/kernel/Image")

    def compile_modules(self):
        print("\n=== 编译 Modules ===")
        env = self._get_env()
        SystemExecutor.run('make modules', cwd=self.ctx.source_dir, env=env)
        SystemExecutor.run('make modules_install', cwd=self.ctx.source_dir, sudo=True, env=env)

    def compile_dtbs(self):
        print("\n=== 编译 DTBs ===")
        env = self._get_env()
        SystemExecutor.run('./tools/l4t_update_initrd.sh', cwd=self.ctx.tegra_dir, sudo=True)
        SystemExecutor.run('make ARCH=arm64 dtbs', cwd=self.ctx.source_dir, env=env)
        SystemExecutor.run(f"cp {self.ctx.source_dir}/kernel-devicetree/generic-dts/dtbs/* {self.ctx.tegra_dir}/kernel/dtb/")

    def update_rootfs(self, module: str):
        print(f"\n=== 更新 Rootfs ({module}) ===")
        SystemExecutor.run('./apply_binaries.sh', cwd=self.ctx.tegra_dir, sudo=True)
        SystemExecutor.run('./tools/l4t_create_default_user.sh -u cnit -p cnit -a -n cnit', cwd=self.ctx.tegra_dir, sudo=True)
        """
        # 优先在当前运行目录找 nv_tools，如果没有，尝试在 tegra_dir 找
        t_dir = os.path.join(self.ctx.original_run_dir, f"nv_tools/tools_{module}/")
        if not os.path.exists(t_dir):
            t_dir = os.path.join(self.ctx.tegra_dir, f"nv_tools/tools_{module}/")
            if not os.path.exists(t_dir):
                print(f"[!] 警告: 未找到 {t_dir}，跳过自定义工具注入")
                return

        SystemExecutor.run(f"echo 'ROOTFS Version: V{self.ctx.rootfs_version} {datetime.now()}' > {self.ctx.ver_file}")
        
        cmds = [
            f"cp -rf {self.ctx.ver_file} rootfs/etc/",
            f"cp -rf {t_dir}01-network-manager-all.yaml rootfs/etc/netplan/",
            f"cp -rf {t_dir}stress/* rootfs/usr/sbin/ && cp -rf {t_dir}stress/compare* rootfs/home/cnit",
            f"cp -rf {t_dir}common/equip_tool rootfs/usr/sbin/",
            f"cp -rf {t_dir}common/loop_emc rootfs/usr/sbin/",
            f"cp -rf {t_dir}common/can/equip_can_fd rootfs/usr/sbin/ && cp -rf {t_dir}common/rs485/rs485 rootfs/usr/sbin/",
            "chmod +x rootfs/usr/sbin/gpu_burn rootfs/usr/sbin/equip_tool rootfs/usr/sbin/loop_emc rootfs/usr/sbin/equip_can_fd rootfs/usr/sbin/rs485",
            f"cp -rf {t_dir}rc.local rootfs/etc/ && chmod 755 rootfs/etc/rc.local",
            f"cp -rf {t_dir}quectel/quectel* rootfs/usr/sbin/ && chmod +x rootfs/usr/sbin/quectel*"
        ]
        if module == "agx": cmds.append(f"cp -rf {t_dir}nvfan/nvfancontrol.conf rootfs/etc/")
        
        for c in cmds: SystemExecutor.run(c, cwd=self.ctx.tegra_dir, sudo=True)
        """
        print(f"[*] {module} Rootfs 更新完毕。")

    def flash_device(self, module: str, ftype: str):
        print(f"\n=== 烧录 {module} 介质: {ftype} ===")
        flash_cmds = {
            "nx": {
                "nvme": "./tools/kernel_flash/l4t_initrd_flash.sh --external-device nvme0n1p1 -c tools/kernel_flash/flash_l4t_t234_nvme.xml -p \"-c bootloader/generic/cfg/flash_t234_qspi.xml\" --showlogs --network usb0 jetson-orin-nano-devkit-super internal",
                "qspi": "./flash.sh --no-systemimg -c bootloader/generic/cfg/flash_t234_qspi.xml jetson-orin-nano-devkit-super nvme0n1p1",
                "only": "./tools/kernel_flash/l4t_initrd_flash.sh --flash-only --network usb0 --massflash 1 --showlogs"
            },
            "agx": {
                "nvme": "./tools/kernel_flash/l4t_initrd_flash.sh --external-device nvme0n1p1 -c tools/kernel_flash/flash_l4t_t234_nvme.xml --showlogs --network usb0 jetson-agx-orin-devkit external",
                "emmc": "./flash.sh jetson-agx-orin-devkit internal",
                "qspi": "./flash.sh --no-systemimg -c bootloader/generic/cfg/flash_t234_qspi.xml jetson-agx-orin-devkit nvme0n1p1",
                "only": "./tools/kernel_flash/l4t_initrd_flash.sh --flash-only --network usb0 --massflash 1 --showlogs"
            }
        }
        cmd = flash_cmds.get(module, {}).get(ftype)
        if not cmd: sys.exit(f"[!] 错误: 模组 {module} 不支持 {ftype} 烧录介质。")
        SystemExecutor.run(cmd, cwd=self.ctx.tegra_dir, sudo=True)

# ==========================================
# 4. 命令行路由总线
# ==========================================
def main():
    description_text = (
        "Jetson Orin 全生命周期构建与烧录平台 (L4T 36.4.3)\n"
        "====================================================\n"
        "提供从底层环境搭建到内核编译、Rootfs 注入及设备烧录的一站式解决方案。"
    )
    
    # 【新增】：在这里配置详尽的常用命令组合 SOP
    epilog_text = """
【常用命令组合示例 (SOP)】
----------------------------------------------------
0. 全新物理机完整构建（强依赖jetpack_env.tar.bz2，慎用）:
   $ python3 build_sdk.py setup
1. 编译指令：
   $ python3 build_sdk.py kernel    编译内核镜像 (Kernel Image)
   $ python3 build_sdk.py modules   编译外树模块 (OOT Modules)
   $ python3 build_sdk.py dtbs      编译设备树 (Device Tree Blobs)
   $ python3 build_sdk.py rootfs nx 将nv_tools/tools_nx注入至Orin NX的Rootfs
   $ python3 build_sdk.py rootfs agx将nv_tools/tools_agx 注入至 AGX Orin 的Rootfs
   $ python3 build_sdk.py all nx    一键全量编译：执行kernel + modules + dtbs并更新NX的Rootfs

2. Orin NX烧录:
   $ python3 build_sdk.py flash nx nvme   # 烧录完整系统至NVMe固态硬盘
   $ python3 build_sdk.py flash nx qspi   # 仅更新QSPI引导程序
   $ python3 build_sdk.py flash nx only   # 执行flash-only操作

3. AGX Orin 烧录:
   $ python3 build_sdk.py flash agx emmc  # 烧录完整系统至内部eMMC
   $ python3 build_sdk.py flash agx nvme  # 烧录完整系统至外部NVMe
   $ python3 build_sdk.py flash agx qspi  # 仅更新QSPI引导程序
   $ python3 build_sdk.py flash agx only  # 执行flash-only操作
    """
    
    parser = argparse.ArgumentParser(
        description=description_text, 
        epilog=epilog_text, 
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    sub = parser.add_subparsers(dest='command', title="核心指令集", description="请选择以下指令之一执行 (例如: python3 build_sdk.py kernel)")
    
    # Day-0 接口
    sub.add_parser('setup', help="[初始化] 一键配置环境依赖与解压源码拓扑")
    
    # Day-1+ 编译接口
    sub.add_parser('kernel', help="[编译] 编译 Kernel 镜像")
    sub.add_parser('modules', help="[编译] 编译外树 Modules")
    sub.add_parser('dtbs', help="[编译] 编译设备树 DTBs")
    
    p_rootfs = sub.add_parser('rootfs', help="[构建] 注入自定义工具并更新指定模组 Rootfs")
    p_rootfs.add_argument('module', choices=['nx', 'agx'], help="目标模组: nx 或 agx")
    
    p_all = sub.add_parser('all', help="[构建] 一键编译所有组件并更新 rootfs")
    p_all.add_argument('module', choices=['nx', 'agx'], help="目标模组: nx 或 agx")
    
    # Day-1+ 烧录接口
    p_flash = sub.add_parser('flash', help="[烧录] 执行设备底层物理烧录")
    p_flash.add_argument('module', choices=['nx', 'agx'], help="目标模组: nx 或 agx")
    p_flash.add_argument('type', choices=['emmc', 'nvme', 'qspi', 'only'], help="烧录介质: emmc (仅agx), nvme, qspi, only")

    # 拦截空输入，打印完美帮助界面
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    ctx = JetsonContext()

    if args.command == 'setup':
        EnvironmentProvisioner(ctx).setup_all()
    else:
        builder = BuildAndFlashManager(ctx)
        if args.command == 'kernel': builder.compile_kernel()
        elif args.command == 'modules': builder.compile_modules()
        elif args.command == 'dtbs': builder.compile_dtbs()
        elif args.command == 'rootfs': builder.update_rootfs(args.module)
        elif args.command == 'all':
            builder.compile_kernel(); builder.compile_modules(); builder.compile_dtbs(); builder.update_rootfs(args.module)
        elif args.command == 'flash':
            if args.module == 'nx' and args.type == 'emmc': sys.exit("[!] 错误: NX 不支持 eMMC。")
            builder.flash_device(args.module, args.type)

if __name__ == "__main__":
    main()