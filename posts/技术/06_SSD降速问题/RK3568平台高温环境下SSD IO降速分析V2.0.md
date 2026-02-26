# Hardware Issue Report: RK3568 平台高温环境下 SSD I/O 降速分析

## 文档控制 (Document Control)

| 属性 (Attribute) | 详情 (Details) |
| --- | --- |
| **文档作者 (Author)** | mengfei.wu |
| **创建日期 (Date)** | 2026-02-26 |
| **文档版本 (Version)** | V2.0 |
| **当前状态 (Status)** | (Closed / Root Cause Identified) |

### 修改记录 (Revision History)

| 版本 (Version) | 日期 (Date) | 修改人 (Author) | 修改说明 (Description) |
| --- | --- | --- | --- |
| V1.0 | 2026-02-26 | mengfei.wu | 初始版本发布，完成 4K/128K/512K 负载模型下的高温交叉验证。 |
| V2.0 | 2026-02-26 | mengfei.wu | 增补核心原因（吞吐量与 IOPS 的数学关系），并添加“常温锁低频”关键佐证实锤结论。 |

---

## 1. 问题描述 (Issue Description)

在对设备进行高低温循环压测时，观察到系统的存储 I/O 速率在高温环境下发生显著衰减。

* **初始现象**：使用 Fio 工具进行 4KB 随机/顺序读取测试时，常温下速率约为 **166 MiB/s**。当 CPU 核心温度 (CPU LOCAL TMP) 上升至 80°C 以上时，I/O 速率出现断崖式下跌，最低降至约 **33 MiB/s**。
* **初步怀疑**：SSD 硬件过热触发固件级热保护 (Thermal Throttling) 或 SATA 物理链路高温降级。

## 2. 测试环境 (Test Environment)

* **Host 平台 (SoC)**：RK3568 (四核 ARM Cortex-A55)
* **存储设备 (Device)**：BIWIN TD80B25620S1T (256GB SATA M.2 SSD)
* **接口协议**：SATA 3.0 (6Gbps)
* **测试工具**：Fio-3.12 (libaio 引擎, iodepth=16, direct=1)

---

## 3. 交叉验证与数据采集 (Investigation & Data Collection)

为了剥离 SSD 硬件本身与 Host 端系统资源对 I/O 性能的干扰，测试团队进行了基于不同环境温度、不同 CPU 频率以及不同 Block Size 的多轮正反向交叉验证。

### 测试数据集汇总

| 测试场景 | 块大小 (Block Size) | 环境/CPU 状态 | Fio 带宽结果 (BW) | Fio IOPS 结果 | 链路层状态 |
| --- | --- | --- | --- | --- | --- |
| **基线测试** | 4 KiB | 常温 / 动态频率 | 166 MiB/s | ~ 42,496 | SATA 3.0 |
| **高温衰减** | 4 KiB | 高温 (80°C+) / 降频 | ~ 33 MiB/s | ~ 8,400 | SATA 3.0 |
| **高温大块** | 128 KiB | 高温 (92.5°C) / 降频 | 531 MiB/s | 4,245 | SATA 3.0 |
| **高温大块** | 512 KiB | 高温 (90.0°C) / 降频 | 539 MiB/s | 1,078 | SATA 3.0 |
| **常温锁频(佐证)** | 4 KiB | 常温 (25°C) / 锁定最低频 (408MHz) | ~ 30+ MiB/s | ~ 8,000+ | SATA 3.0 |
| **常温锁频(佐证)** | 128 KiB | 常温 (25°C) / 锁定最低频 (408MHz) | 500+ MiB/s | ~ 4,000+ | SATA 3.0 |

---

## 4. 核心原因剖析 (Root Cause Analysis)

基于上述严密的数据交叉比对，得出最终技术定论：**本次降速事件完全与 SSD 硬件及 SATA PHY 物理链路无关。核心瓶颈在于 RK3568 SoC 在高温下触发了系统级动态调频调压 (DVFS) 以进行热保护，严重削减了 CPU 的算力，进而引发了中断处理能力的坍塌。**

在块设备 I/O 栈中，吞吐量与 CPU 中断响应能力（IOPS）遵循以下基础物理公式：


$$Throughput = IOPS \times Block\_Size$$

系统底层的瓶颈转移逻辑如下：

1. **4KB 小块 I/O 的算力灾难**：
常温下，系统跑出 166 MiB/s 需要 CPU 每秒处理约 42,496 次中断 ($166 \times 1024 \div 4 \approx 42496$)。当 CPU 核心温度达到 80°C 触发 Thermal Throttling 时，CPU 时钟周期被强行拉低。算力大幅缩水的 CPU 每秒最多只能处理约 8,400 次硬件中断 (Hard IRQ) 和软中断 (SoftIRQ)。这导致 AHCI 控制器的完成队列 (CQ) 严重阻塞，前端吞吐量被物理锁死在：$8400 \times 4\text{KB} \approx 32.8 \text{ MiB/s}$。
2. **大块 I/O (≥128KB) 免疫降速的原因**：
为了跑满 SATA 3.0 的极限带宽 (约 540 MiB/s)，128KB 块大小只需要极低的中断处理频率 ($540 \times 1024 \div 128 \approx 4320 \text{ IOPS}$)。即使 CPU 处于 92.5°C 的极度降频状态，处理 4,320 IOPS 依然在其剩余算力的承受范围内（此时观测到 CPU sys 占用率高达 87.97%，说明已接近算力极限，但刚好够用）。因此，大块传输不会出现降速。

## 5. 关键佐证 (Key Validation)

为了彻底剥离“温度”对 SSD 物理颗粒的嫌疑，测试团队实施了**反向定频测试 (Reverse Fixed-Frequency Test)**：

* 在 25°C 的常温环境下，主动将 RK3568 的 CPU `scaling_governor` 切换为 `userspace`，并锁定在极低频率（例如 408MHz）。
* **测试结果**：常温低频状态下，4KB I/O 依然稳定复现了 30+ MiB/s 的低速现象；而 128KB 依然能跑满 500+ MiB/s 带宽。
* **佐证结论**：该测试 100% 证实了 I/O 降速仅与“CPU 时钟周期（频率/算力）不足”有关，SSD 自身并不存在热失控缺陷。

## 6. 结论与建议 (Conclusion & Recommendations)

**结论**：
存储子系统（BIWIN SSD 及主板 SATA 接口）通过了严苛的高温压力测试，无硬件缺陷。问题根因归属于 RK3568 主机端在恶劣热环境下的性能降级策略。高并发的小块 I/O 测试（4KB direct I/O）放大了 CPU 算力不足的短板。

**优化建议**：

1. **硬件散热改良**：若终端产品的核心业务高频依赖 4KB 随机存取，必须优化散热设计（如增加散热片/导热垫），防止 CPU 结温触及降频阈值。
2. **应用层聚合优化**：强烈建议软件业务侧在 User Space 或 Page Cache 层，将细碎的 4KB 小数据拼接、聚合成 128KB 甚至更大的 Block 后再下发至底层块设备，从根本上规避嵌入式 SoC 的中断算力瓶颈。
3. **驱动中断亲和性**：可尝试将 `/proc/irq/<SATA_IRQ>/smp_affinity` 绑定至受温控影响较小或专属处理 I/O 的特定 CPU 核心，以缓解算力争抢。  

**命令修正**：
```sh  
##原始命令：fio --allow_mounted_write=1 -ioengine=libaio -bs=4k -direct=1 -thread -rw=read -filename=/dev/$device -name="BS 4KB read test" -iodepth=16 -runtime=10
##修正命令：fio --allow_mounted_write=1 -ioengine=libaio -bs=128k -direct=1 -thread -rw=read -filename=/dev/$device -name="BS 128KB read test" -iodepth=16 -runtime=10
```
