---
title: Jetson AGX Orin 自定义风扇 (WT-949) 适配设计方案
date: 2026-02-15
category: 技术
tags: 工具, 效率, 推荐
summary: 适配WT-949风扇转速配置方案
---
# Jetson AGX Orin 自定义风扇 (WT-949) 适配设计方案

**文档信息**

* **作者**: mengfei.wuuuu@gmail.com
* **日期**: 2026-02-25
* **版本**: V1.0

## 修订记录 (Revision History)

| 版本 | 日期 | 作者 | 修改描述 |
| --- | --- | --- | --- |
| V1.0 | 2026-02-25 | mengfei.wuuuu@gmail.com | 初版发行：基于实测 4200 RPM 数据，完成 WT-949 风扇在 JetPack 6.2 下的设备树及 `nvfancontrol` 策略设计。 |

---

## 1. 概述

* **目标平台**：NVIDIA Jetson AGX Orin
* **系统环境**：JetPack 6.2 / L4T 36.4.3 / Linux Kernel 5.15.148
* 
**适配外设**：WT-949 散热器 ，核心风扇模块为奇凌 (CoolCox) CC8010H12D 支架风扇 。


* 
**背景与需求**：出厂默认的风扇配置参数无法完美驱动并精准调控该第三方风扇。规格书标称转速为 3600 RPM ，但实际测试发现最高物理转速达到 4200 RPM，且驱动默认的 PWM 频率（50kHz）与风扇推荐的 25kHz  不匹配。本方案旨在通过修改设备树 (Device Tree) 与系统控制策略 (`nvfancontrol.conf`)，实现对该风扇的精准、稳定调控。



---

## 2. 硬件接线规范 (⚠️ 警告)

**关键风险提示**：该风扇的线序颜色定义与标准工控机/PC 4-Pin 风扇规范**完全不同**。在连接至载板前，**必须进行跳线或重新排线**，切勿盲插，否则有烧毁主板 IO 或风扇的风险。

根据供应商提供的规格书，线序定义如下 ：

* 
**Pin 1 (黑色)**：PWM 控制信号 


* 
**Pin 2 (红色)**：FG (Tach/测速信号) 


* 
**Pin 3 (黄色)**：GND (电源负极) 


* 
**Pin 4 (蓝色)**：12V (电源正极) 



*实施要求*：请研发人员仔细核对 AGX Orin 载板的风扇接口丝印（通常为 1-GND, 2-12V, 3-TACH, 4-PWM），按功能严格对插。

---

## 3. 设备树 (Device Tree) 适配

为满足风扇的电气特性，需在内核设备树中调整 PWM 发生器的频率以及风扇转速读取的脉冲系数。

### 3.1 核心修改点

1. 
**PWM 频率调整**：规格书建议 PWM 控制频率为 25kHz 。需将 `period-ns` 属性修改为 `40000` (计算：$10^9 / 25000 = 40000$ ns)。


2. 
**转速校准 (PPR)**：该风扇电机为 4 极 (4 Poles) ，通常每转输出 2 个脉冲。需明确声明 `pulses-per-revolution = <2>;`，以修复系统读取转速虚高的问题。


3. **驱动状态映射**：补全 `cooling-levels`，以便系统能够正确下发 PWM 占空比。

### 3.2 节点代码参考

定位到当前使用的 `.dts` 或 `.dtsi` 文件中定义 `pwm-fan` 的节点，修改如下：

```dts
fan: pwm-fan {
    compatible = "pwm-fan";
    /* 使用 pwm3 控制器，通道 0，周期 40000ns (25kHz) */
    pwms = <&pwm3 0 40000>;
    
    /* 建立 PWM 占空比的冷却等级映射 (0-255) */
    cooling-levels = <0 64 128 192 255>;
    
    /* 适配 4 极电机，配置每转脉冲数为 2 */
    pulses-per-revolution = <2>;

    /* (可选) 根据具体载板的硬件设计，补充 FG 测速引脚的中断映射 */
    /* interrupts-extended = <&gpio_aon TEGRA234_AON_GPIO(PE, 0) IRQ_TYPE_EDGE_FALLING>; */
    
    #cooling-cells = <2>;
};

```

---

## 4. 风扇控制策略配置 (nvfancontrol.conf)

JetPack 使用 `nvfancontrol` 用户态服务进行闭环控制。由于系统启用了 `TMARGIN`（热裕量）模式，且实测风扇最高转速达 4200 RPM，需要重写映射曲线。

### 4.1 控制逻辑说明

* **TMARGIN 模式**：表格中的 `TEMP` 代表“距离降频温度的余量”。`0` 代表最热（需全速运转），数值越大代表越冷。
* **容差放宽**：由于 4200 RPM 基数较大，需将 `RPM_TOLERANCE` 放大至 400，避免 PID 控制器因小幅抖动而产生失效日志。
* 
**Kickstart**：启动脉冲设为 `77` (约 30% PWM)，对应规格书中约 1900 RPM 的物理档位 ，保证风扇冷启动时不卡顿。



### 4.2 配置文件内容

请将以下内容写入 `/etc/nvfancontrol.conf`：

```ini
POLLING_INTERVAL 2

<FAN 1>
    TMARGIN ENABLED
    FAN_GOVERNOR pid {
        STEP_SIZE 10
    }
    FAN_GOVERNOR cont {
        STEP_SIZE 10
    }
    FAN_CONTROL close_loop {
        # 放宽转速容差，适配 4200 RPM 的高转速基数
        RPM_TOLERANCE 400
    }

    # === 性能散热模式 (Cool) ===
    FAN_PROFILE cool {
        # TEMP(热裕量)    HYST    PWM    RPM
        # 极热状态：满负荷运行
        0       0       255    4200
        10      0       255    4200
        # 高负载：约 70% 占空比
        30      0       179    3300
        # 中负载：约 50% 占空比
        45      0       128    2600
        # 低温待机：最低转速 (规格书表明 0% PWM 对应 1150 RPM)
        60      0       0      1150
        105     0       0      1150
    }

    # === 静音模式 (Quiet) ===
    FAN_PROFILE quiet {
        # TEMP(热裕量)    HYST    PWM    RPM
        # 极热保护
        0       0       255    4200
        # 稍有余量即迅速降速减噪
        15      0       204    3800
        30      0       77     1900
        # 低温待机
        60      0       0      1150
        105     0       0      1150
    }

    THERMAL_GROUP 0 {
        GROUP_MAX_TEMP 105
        # CPU, GPU 等核心 Thermal-Zone 映射
        CPU-therm 20,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 0
        GPU-therm 20,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 0
        SOC0-therm 20,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 0
        SOC1-therm 20,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 0
        SOC2-therm 20,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 0
    }

    FAN_DEFAULT_CONTROL close_loop
    FAN_DEFAULT_PROFILE cool
    FAN_DEFAULT_GOVERNOR cont
    
    # 启动脉冲：30% PWM，确保启转可靠
    KICKSTART_PWM 77
</FAN 1>

```

---

## 5. 部署与验证步骤

1. **更新设备树**：编译修改后的 DTS 并将其刷写（Flash）到设备或通过 FDT Overlay 动态加载，重启系统生效。
2. **更新配置**：将上述配置文件覆盖系统路径 `/etc/nvfancontrol.conf`。
3. **清理旧状态**：执行命令 `sudo rm /var/lib/nvfancontrol/status` 删除系统自动生成的历史运行缓存。
4. **重启服务**：执行 `sudo systemctl restart nvfancontrol` 重新加载策略。
5. **系统验证**：
* 运行 `sudo nvfancontrol -q` 查看当前生效的 Profile、目标转速与实际转速闭环情况。
* 运行 `jtop` 工具，在第 5 页 (CTRL) 观察风扇 PWM 与 RPM 的实时响应及稳定性。



---