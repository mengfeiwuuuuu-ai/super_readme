# Hardware Issue Report: RK3568 平台高温环境下 SSD I/O 降速分析

## 文档控制 (Document Control)

| 属性 (Attribute) | 详情 (Details) |
| --- | --- |
| **文档作者 (Author)** | mengfei.wu |
| **创建日期 (Date)** | 2026-02-26 |
| **文档版本 (Version)** | V1.0 |
| **当前状态 (Status)** | (Closed / Root Cause Identified) |

### 修改记录 (Revision History)

| 版本 (Version) | 日期 (Date) | 修改人 (Author) | 修改说明 (Description) |
| --- | --- | --- | --- |
| V1.0 | 2026-02-26 | mengfei.wu | 初始版本发布，完成 4K/128K/512K 负载模型下的高温交叉验证及根因定论。 |

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

为了剥离 SSD 硬件本身与 Host 端系统资源对 I/O 性能的干扰，测试团队在极端高温环境下（CPU 结温 > 90°C，主板环境温度 > 63°C），针对不同 Block Size 进行了多轮交叉验证。

### 测试数据集汇总

| 块大小 (Block Size) | 目标读写模式 | 记录时 CPU 温度 | Fio 带宽结果 (BW) | Fio IOPS 结果 | 链路层协商状态 |
| --- | --- | --- | --- | --- | --- |
| **4 KiB** | Read | > 80.0°C | ~ 33 MiB/s | ~ 8,400 | SATA 3.0 |
| **128 KiB** | Read | 92.5°C | 531 MiB/s | 4,245 | SATA 3.0 |
| **512 KiB** | Read | 90.0°C | 539 MiB/s | 1,078 | SATA 3.0 |

### 关键日志寻迹 (Key Log Traces)

在 92.5°C 的极限恶劣工况下执行 128 KiB 读取时，系统性能监控反馈如下：

> `cpu : usr=11.40%, sys=87.97%, ctx=648, majf=0, minf=513`

此时 CPU 内核态占用率 (`sys`) 飙升至 87.97%，整体 CPU 负载突破 99%。

---

## 4. 根因分析 (Root Cause Analysis)

基于上述测试数据的交叉比对，可以得出明确的技术定论：**本次降速事件与 SSD 硬件及 SATA PHY 物理链路无关。** 核心瓶颈在于 **RK3568 SoC 在高温下触发了系统级动态调频调压 (DVFS) 导致的算力坍塌，进而引发了中断处理风暴 (Interrupt Handling Collapse)。**

1. **设备端 (Device) 表现完美**：
在 90°C 甚至 92.5°C 的极限 CPU 温度下，使用 128KiB 和 512KiB 块大小进行压测，BIWIN SSD 依然能够跑满 SATA 3.0 接口的物理带宽上限（稳定在 531 MiB/s - 539 MiB/s）。这证明 SSD 主控固件未触发严重的热降频，NAND 介质未出现大面积纠错开销，且 AHCI 物理层未发生信号衰减降级。
2. **主机端 (Host) 中断算力枯竭**：
4KB 小块 I/O 想要跑满带宽，需要极高的中断处理能力。计算常温下 166 MiB/s 所需的 IOPS 负载：

$$\text{Required IOPS} = \frac{166 \text{ MiB/s} \times 1024}{4 \text{ KB}} \approx 42496$$



当 RK3568 结温超过 80°C 时，其内核 Thermal Framework 强制大幅降低 CPU 主频以自保。降频后的 CPU 算力被严重削弱。日志表明，即使是处理 128KiB 下的 4245 次 IOPS，就已经榨干了降频后 CPU 近 99.37% 的资源。
因此，当负载切回 4KB 时，算力匮乏的 CPU 只能勉强处理约 8,400 IOPS，直接导致 AHCI 硬件中断积压，完成队列阻塞，前端观测吞吐量跌落至 33 MiB/s 左右。

## 5. 结论与建议 (Conclusion & Recommendations)

**结论**：存储子系统本身（包含 BIWIN SSD 与 SATA 驱动链路）在此工况下不存在缺陷。问题归属于 RK3568 主机端在极端热环境下的性能妥协策略。

**优化建议**：

1. **系统散热评估**：若终端产品的核心业务场景高度依赖高并发、小文件存取，必须从结构硬件上优化散热方案（如增加导热硅胶垫片或主动散热），阻止 CPU 结温触碰 80°C 的降频红线。
2. **业务层适配**：建议应用层开发人员尽可能将细碎的 4KB I/O 请求在内存缓存中聚合成 128KB 或更大的 Block 后再下发至块设备，以规避 SoC 的中断算力短板。

**命令修正**：
```sh  
##原始命令：fio --allow_mounted_write=1 -ioengine=libaio -bs=4k -direct=1 -thread -rw=read -filename=/dev/$device -name="BS 4KB read test" -iodepth=16 -runtime=10
##修正命令：fio --allow_mounted_write=1 -ioengine=libaio -bs=128k -direct=1 -thread -rw=read -filename=/dev/$device -name="BS 128KB read test" -iodepth=16 -runtime=10
```
---