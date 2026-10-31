# SEGGER RTT（实时传输）中文摘录

> 原文：[https://kb.segger.com/RTT](https://kb.segger.com/RTT)（SEGGER Knowledge Base）
> 本文为原文的中文翻译摘录，保留了技术结构与关键参数；代码保持原样，仅注释做中文说明。个别原文自相矛盾之处已用「译注」标出。

---

## 目录

- [1. 概述](#1-概述)
- [2. RTT 的工作原理](#2-rtt-的工作原理)
  - [2.1 RTT 控制块](#21-rtt-控制块)
  - [2.2 缓冲区](#22-缓冲区)
  - [2.3 需求条件](#23-需求条件)
  - [2.4 性能](#24-性能)
  - [2.5 内存占用](#25-内存占用)
- [3. 控制块的定位](#3-控制块的定位)
- [4. RTT 通道](#4-rtt-通道)
- [5. RTT 运行模式](#5-rtt-运行模式)
- [6. 各内核注意事项](#6-各内核注意事项)
- [7. 实现与 API](#7-实现与-api)
- [8. 配置宏](#8-配置宏)
- [9. 性能优化](#9-性能优化)
- [10. ARM Cortex 的背景内存访问](#10-arm-cortex-的背景内存访问)
- [11. 示例代码](#11-示例代码)
- [12. 主机端通信](#12-主机端通信)
- [13. 低功耗模式](#13-低功耗模式)
- [14. 常见问题排查](#14-常见问题排查)
- [15. FAQ](#15-faq)

---

## 1. 概述

SEGGER 的 **RTT（Real Time Transfer，实时传输）** 是一种用于嵌入式应用中交互式用户 I/O 的技术。它结合了 SWO 与 semihosting（半主机）两者的优点，并且性能极高。

借助 RTT，可以极高速地从目标单片机输出信息，同时也能向应用发送输入，而**不影响目标的实时行为**。

- SEGGER RTT 可用于**任意 J-Link 型号**，以及任何支持背景内存访问的被支持目标处理器（即 Cortex-M 和 RX 目标）。
- RTT 支持**双向多通道**（上行至主机、下行至目标），可用于不同用途，给用户最大的自由度。
- 默认实现每个方向使用一个通道，用于可打印的终端输入/输出。配合 **J-Link RTT Viewer**，该通道可拆分为多个「虚拟」终端，从而仅用一个目标缓冲区就能向多个窗口输出（例如：标准输出、错误输出、调试输出各一个窗口）。
- 额外的上行通道可用于发送性能剖析（profiling）或事件跟踪数据（例如供 **SEGGER SystemView** 使用）。

---

## 2. RTT 的工作原理

RTT 在 RAM 中使用一个 **RTT 控制块（Control Block）** 结构，并为每个通道的每个已配置方向使用**环形缓冲区**。可用通道的最大数量在编译期配置，而每个缓冲区可在运行期由应用配置并添加。

- 上行（Up）与下行（Down）缓冲区可分别独立处理。
- 每个通道可配置为**阻塞**或**非阻塞**：
  - **阻塞**：不会丢数据，但可能暂停应用。
  - **非阻塞**：多余信息被丢弃，使应用即使在未连接调试器时也能实时运行。

### 2.1 RTT 控制块

RTT 控制块（CB）包含多个元素以支撑 RTT 工作，位于 RAM 中。它**总是以一个 ID 开头**，该 ID 用于：

- 让连接的 J-Link 能在内存中（自动）检测到该 CB；
- 对 CB 做有效性校验。

ID 之后是**缓冲区描述符（Buffer Descriptors）**，其中保存了所有必需的 RTT 通道信息。

#### 缓冲区描述符

缓冲区描述符提供各通道环形缓冲区的信息，J-Link 通过它从目标读取数据、向目标写入数据。上行（Target → Host）和下行（Host → Target）缓冲区描述符的数量可以任意，直到允许的最大通道数。

对于**上行缓冲区**：

- 写指针**只由目标**写入；
- 读指针**只由调试探头（J-Link / Host）**写入。

对于**下行缓冲区**：

- 写指针**只由调试探头（J-Link / Host）**写入；
- 读指针**只由目标**写入。

这样可确保不会发生竞态条件。当读指针与写指针指向同一元素时，缓冲区为空。

### 2.2 缓冲区

环形缓冲区同样位于 RAM，但**不属于** RTT 控制块。缓冲区大小可按每个通道、每个方向单独配置。

### 2.3 需求条件

除了一台通过标准调试口连接到目标的 J-Link 之外，SEGGER RTT **不需要任何额外的引脚或硬件**。它不需要对目标或调试环境做任何配置，甚至可以配合变化的目标速度使用。

RTT 可以在正在进行的调试会话中并行使用（无侵入），也完全可以脱离任何 IDE 或调试器使用。

### 2.4 性能

SEGGER RTT 的性能显著高于任何其他向主机 PC 输出数据的技术。**平均一行文本可在 1 微秒或更短时间内输出**——基本上只相当于做一次 `memcpy()` 的时间。

### 2.5 内存占用

- 代码（ROM）：约 **500 字节**
- 控制块（RAM）：**24 字节 ID + 每通道 24 字节**
- 每个通道还需缓冲区内存。推荐大小：上行通道 **1 KB**；下行通道 **16～32 字节**（取决于输入/输出负载）。

---

## 3. 控制块的定位

RTT 允许 J-Link 在给定 RAM 范围内（自动）检测控制块。默认使用自动检测，但用户也可以提供具体的控制块地址，或指定要搜索的 RAM 范围。

当主机侧 RTT 处于活动状态时（无论是通过 J-Link RTT Viewer 这类应用直接使用 RTT，还是通过 Telnet 连接到使用 J-Link 的应用如调试器），J-Link 会通过以下位置自动搜索 SEGGER RTT 控制块：向量表中指定的地址、J-Link 软件指定的目标 RAM 区域（自动检测），和/或用户选择的区域。

### 3.1 自动检测

默认使用自动检测定位 CB。J-Link 会**首先尝试在向量表偏移 `0x20` 处**查找控制块地址（该地址应加 `0x2` 以标记为有效的 RTT 控制块地址）。若找不到，J-Link 将在 J-Link 软件已知的指定目标的 RAM 中搜索。

> **注意**
> 对大多数 MCU，选择自动检测时**并不会搜索所有 RAM 区域**，原因包括：
> - 搜索区域越大，定位控制块耗时越长（RAM 巨大的目标上可能 > 30 秒）；
> - 某些 RAM 区域并非时刻可用，访问未激活的区域可能导致未定义行为或 HardFault：
>   - RAM 可能是可配置的；
>   - RAM 在某些 MCU 状态下不可访问（如 TrustZone 安全/非安全区域）；
>   - RAM 可能默认未使能，或被用户禁用；
>   - RAM 可能无法通过所选 MEM-AP 访问（仅非 Cortex-M 目标）；
>   - ……

### 3.2 手动指定控制块位置

虽然自动检测在多数情况下工作良好，但始终可以手动指定控制块的**确切位置**，或 J-Link 应搜索的**地址范围**。方式包括：

- 使用 J-Link 命令字符串（例如在 J-Link 脚本文件中）：
  - `SetRTTAddr`
  - `SetRTTSearchRanges`
- 通过所用工具（若支持），例如 J-Link RTT Viewer 的配置对话框；
- 通过 J-Link 的 TELNET 通道。

---

## 4. RTT 通道

> **注意**：本节讨论的是 RTT **通道（Channel）**，不要与 RTT 终端（Terminal）混淆。

一个 RTT 通道由一个配置和一个环形缓冲区组成，用于某一特定方向的数据传输（上行：Target → Host；下行：Host → Target）。

### 4.1 通道配置

上行与下行通道可分别独立配置：

- **通道缓冲区大小**：用于数据传输的通道缓冲区尺寸。
- **通道缓冲区模式**（见下）。

> **注意：RTT 通道 0 比较特殊**
> - 它在**编译期**配置，并在调用 `SEGGER_RTT_Init()` 或任一 RTT 写函数时立即建立——目的是开箱即用，无需手动设置。
> - 通道 0 使用「RTT 配置」小节中提到的参数宏建立。
> - 对通道 0，**只有 flags 可以手动（重新）配置**；调用 `SEGGER_RTT_ConfigDownBuffer()` / `SEGGER_RTT_ConfigUpBuffer()` 时其余配置参数都会被忽略。
> - 其他所有通道都需要用 `SEGGER_RTT_ConfigDownBuffer()` / `SEGGER_RTT_ConfigUpBuffer()` 手动建立各自的缓冲区。

#### 通道缓冲区模式

共 3 种模式（1 种阻塞 + 2 种非阻塞）：

- **阻塞模式**：缓冲区满时应用会等待，直到所有数据写入完毕；应用处于阻塞状态，但不会丢数据。
- **非阻塞模式**：只写入能放进缓冲区的数据（或完全不写），其余被丢弃。

这样即使没有连接调试器也能实时运行，开发者无需专门做一个调试版本，代码可以原样保留在发布版中。

| 定义 | 含义 |
| --- | --- |
| Blocking（阻塞） | 缓冲区满时应用等待，直到所有数据写入完毕；应用阻塞，但不丢数据。 |
| Non-blocking, skip（非阻塞-跳过） | 若上行缓冲区空间不足以容纳全部输入数据，则**全部丢弃**。 |
| Non-blocking, trim（非阻塞-截断） | 若上行缓冲区空间不足，则**填满可用空间，剩余丢弃**。 |

---

## 5. RTT 运行模式

SEGGER RTT 有三种运行模式。（不要与「通道缓冲区配置模式」混淆。）

| 模式 | 说明 | 探头支持 |
| --- | --- | --- |
| **Background mode**（背景模式） | 最快的模式，传输速度可达约 **3.5 MB/s**（译注：原文正文又写作最高 2 MB/s，两处数值不一致） | 所有当前 J-Link / J-Trace Pro 型号 |
| **Legacy background mode**（传统背景模式） | 背景模式的旧版，探头固件侧没有相应处理，传输速度较低 | 所有当前 Flasher 型号；J-Link Base / Plus < V9；J-Link Pro / Ultra+ < V4；J-Trace Pro < V2 |
| **Stop mode**（停止模式） | 伪 RTT 模式，读取数据时暂停 CPU；为不支持背景访问的 CPU 引入 | 所有 J-Link / J-Trace Pro / Flasher 型号 |

### 5.1 背景模式（Background mode）

与传统背景模式相同，但在**探头固件侧**增加了实现，因此传输速度显著更高（最高约 2 MB/s）。

### 5.2 传统背景模式（Legacy background mode）

这是 RTT 最初引入时的模式。在此模式下，J-Link 可以在 MCU 与应用持续运行的同时访问目标系统内存（背景内存访问），实际上不影响应用的实时行为。使用该模式要求目标 MCU 支持背景内存访问。

**支持背景模式的内核：**

- Cortex-M（受支持内核列表见 SEGGER 官网）
- 瑞萨 RX 系列器件
- Cortex-A 32 位（ARMv7-A）（可选，见「Cortex-A 注意事项」）
- Cortex-R 32 位（ARMv7-R）（可选，见「Cortex-R 注意事项」）
- RISC-V（可选，见「RISC-V 注意事项」）

### 5.3 停止模式（Stop mode）

在此模式下，J-Link 临时暂停 CPU（中断目标应用执行）以访问内存，访问完成后自动继续运行。对实时行为的实际影响（暂停时长）取决于具体设置（目标接口速度、所用接口、JTAG 链长度、实际内核等）。

该模式自 **J-Link 软件 V6.30** 引入，用于在不支持背景内存访问的器件/CPU 架构上也能使用 RTT。它会影响应用实时性，但多数目标应用仍可使用。

**支持停止模式的内核：**

- Cortex-A 系列器件（**仅** ARMv7-A）
- Cortex-R 系列器件（**仅** ARMv7-R）
- RISC-V 系列器件

> **注意**
> - ARMv8-AR 上**不支持**停止模式。
> - 建议仅在目标接口速度 **≥ 25 MHz**（J-Link ULTRA+、J-Link PRO）时使用该模式，以尽量减小对实时性的影响。

#### 对实时行为的影响（实测暂停时间）

**J-Link ULTRA+ @ 50 MHz** 下停止模式内存读访问的典型暂停时间：

- JTAG @ 50 MHz，256 字节：约 **552 µs**
- JTAG @ 50 MHz，4 字节：约 **418 µs**

**J-Link PLUS @ 15 MHz** 下：

- JTAG @ 15 MHz，256 字节：约 **1.02 ms**
- JTAG @ 15 MHz，4 字节：约 **718 µs**

---

## 6. 各内核注意事项

### 6.1 Cortex-M 特别说明

若 CPU 带有 cache：

- RTT 控制块及所有 RTT 缓冲区必须**按 cache line 对齐起始**；
- 控制块及所有缓冲区的大小必须是 **cache line 的整数倍**；
- 若系统有多级 cache，对齐与尺寸应以**行大小最大的 cache** 为基准；
- 控制块与上/下行缓冲区 0 由 `SEGGER_RTT.c` 隐式定义。因此若系统 cache line 不大于 32 字节，需指定 `SEGGER_RTT_CPU_CACHE_LINE_SIZE`，以确保满足对齐要求；
- **由用户应用负责**：在段初始化完成后、首次使用 RTT 之前，对 RTT 控制块及所有 RTT 缓冲区执行 cache clean + invalidate。合适的时机是在 `main()` 中。这可确保没有 cache line 残留脏的 RTT 数据/信息（否则可能在运行期某刻被回写到内存）。若使用 embOS，通常在 `OS_InitHW()` 调用之后再使用 RTT 是安全的（该函数会对所有 cache line 做 clean + invalidate）；
- 对于运行期指定并初始化的 RTT 缓冲区（索引 > 0），必须在调用任何 `AllocBuffer()` / `ConfigBuffer()` 函数**之前**执行 cache clean + invalidate；
- 在应用中，RTT 控制块、缓冲区及其名称指针的链接必须满足**虚拟地址 == 物理地址**；
- 应用必须为存放控制块+缓冲区的内存提供**非缓存地址别名（uncached alias）**，控制块及所有缓冲区都需能通过该别名访问。

### 6.2 Cortex-A 特别说明

- RTT 背景内存访问通过 **BG MEM-AP**（AHB-AP 或 AXI-AP）进行；
  - AHB-AP / AXI-AP 是否存在是可选的，取决于实际 MCU（厂商是否实现）；
- 对于 J-Link 不知道「可用于 RTT 的 AP」的器件：
  - 需通过 **J-Link 脚本文件**指定用于背景内存访问的 AP；
- 控制块与缓冲区必须放在可通过 BG MEM-AP 访问的 RAM 中；
- **强烈建议**将 RTT 控制块与缓冲区放在**内部存储器**而非外部存储器。Cortex-A 系统上，外部地址空间通常很敏感，若在初始化完成前被访问（如 DDR 控制器尚未初始化）很容易造成锁死。由于 J-Link 无法得知外部内存何时初始化完成，因此存在 J-Link 侧在外部内存可用之前就访问 RTT 的潜在风险；
- AHB/AXI-AP 访问的行为类似 **DMA** 访问，会**旁路 CPU 的 L1/L2 等 cache**；
- 若 CPU 带 cache，参见「Cortex-M 特别说明」。

**Cortex-A MCU 示例（开箱即支持 RTT）：**

- Xilinx Zynq 7000 系列，基于 Cortex-A9（RTT 自 V6.85b 起支持）
- NXP i.MX6Solo 系列，基于 Cortex-A9，器件名模式：`MCIMX6Sx`（RTT 自 V6.85d 起支持）

emPower Zynq 板的示例工程要求：SEGGER Embedded Studio V5.10a 或更高、J-Link 软件 V6.85b 或更高。

### 6.3 Cortex-R 特别说明

Cortex-R 上的 RTT 与「Cortex-A 特别说明」相同。

### 6.4 RISC-V 特别说明

- RTT 背景内存访问可通过 **RISC-V 系统总线访问（SBA）**或 **AHB/AXI-AP** 进行；
- SBA 支持是可选的，取决于实际 MCU；
- AHB/AXI-AP 访问仅在 RISC-V 内核位于 ARM CoreSight DAP 之后时可行。

**通过 SBA 支持：**

- 无需特殊设置。J-Link 会自动检测 SBA 支持并可直接使用 RTT。

**通过 MEM-AP 支持：**

- AHB-AP / AXI-AP 是否存在是可选的，取决于实际 MCU；
- 该访问方式自 **J-Link 软件 V7.50** 起支持；
- 对于 J-Link 不知道「可用于 RTT 的 AP」的器件，需通过 J-Link 脚本文件指定 AP；
- 强烈建议将控制块与缓冲区放在内部存储器（理由同 Cortex-A）；
- AHB/AXI-AP 访问类似 DMA，旁路 L1/L2 cache；
- 若 CPU 带 cache，规则同「Cortex-M 特别说明」。

### 6.5 ARMv8-AR 上选择 MEM-AP

参见 SEGGER KB 的「ARMv8-AR 调试特别说明」页面。

---

## 7. 实现与 API

RTT 实现代码用 **ANSI C** 编写，只需把源码加入工程即可集成到任何嵌入式应用。

- 通过简单易用的 API 使用，甚至可以把标准 `printf()` 重定向到 RTT；
- 使用 RTT 可将输出耗时降到最低，使应用在执行时间关键的实时任务时也能向主机打印调试信息；
- 内置一个精简版 `printf()`，可经 RTT 输出格式化字符串。它比大多数标准库实现更小，**不需要堆**，只占用可配置的少量栈；
- 实现完全可通过预处理器宏在编译期配置：通道数量、默认通道大小均可设定；读写可通过可定义的 `Lock()` / `Unlock()` 例程实现任务安全。

### 7.1 源码下载

RTT 源码位于 SEGGER GitHub：<https://github.com/SEGGERMicro/RTT>

### 7.2 RTT 初始化

> **注意**
> RTT 实现期望控制块所在 RAM 处于以下两种状态之一：
> 1. **已清零（0 初始化）**，即 RTT 尚未建立——这是多数用户的默认情形；
> 2. **已存在建立好的控制块**——用于多应用共享控制块的场景，如 bootloader + 主应用。
>
> 除此之外的任何情况，**必须**先调用 `SEGGER_RTT_Init()`，再调用其他 RTT 函数！

### 7.3 API 函数

使用前需在调用源文件中包含 `SEGGER_RTT.h`。

函数清单：`SEGGER_RTT_ConfigDownBuffer()`、`SEGGER_RTT_ConfigUpBuffer()`、`SEGGER_RTT_GetKey()`、`SEGGER_RTT_HasKey()`、`SEGGER_RTT_Init()`、`SEGGER_RTT_printf()`、`SEGGER_RTT_Read()`、`SEGGER_RTT_SetTerminal()`、`SEGGER_RTT_TerminalOut()`、`SEGGER_RTT_WaitKey()`、`SEGGER_RTT_Write()`、`SEGGER_RTT_WriteString()`、`SEGGER_RTT_GetAvailWriteSpace()`。

---

#### 7.3.1 `SEGGER_RTT_ConfigDownBuffer()`

通过指定名称、大小和标志来配置或添加一个下行缓冲区。

```c
int SEGGER_RTT_ConfigDownBuffer (unsigned BufferIndex, const char* sName,
                                 char* pBuffer, int BufferSize, int Flags);
```

| 参数 | 含义 |
| --- | --- |
| `BufferIndex` | 要配置的缓冲区索引。必须小于 `SEGGER_RTT_MAX_NUM_DOWN_CHANNELS`。 |
| `sName` | 以 0 结尾的字符串指针，作为通道名显示。 |
| `pBuffer` | 该通道使用的缓冲区指针。 |
| `BufferSize` | 缓冲区大小（字节）。 |
| `Flags` | 通道标志（阻塞/非阻塞）。`Flags[31:24]`：有效性校验用，必须为 0；`Flags[23:2]`：保留；`Flags[1:0]`：RTT 运行模式。 |

**返回值**：`>= 0` 成功；`< 0` 错误。

**示例**

```c
// 配置下行缓冲区 1
SEGGER_RTT_ConfigDownBuffer(1, "DataIn", &abDataIn[0], sizeof(abDataIn),
                            SEGGER_RTT_MODE_NO_BLOCK_SKIP);
```

**补充**：缓冲区配置完成后，后续只应修改其 flags。

---

#### 7.3.2 `SEGGER_RTT_ConfigUpBuffer()`

通过指定名称、大小和标志来配置或添加一个上行缓冲区。

```c
int SEGGER_RTT_ConfigUpBuffer (unsigned BufferIndex, const char* sName,
                               char* pBuffer, int BufferSize, int Flags);
```

参数含义同 `ConfigDownBuffer`（索引上限为 `SEGGER_RTT_MAX_NUM_UP_CHANNELS`）。

**返回值**：`>= 0` 成功；`< 0` 错误。

**示例**

```c
// 配置上行缓冲区 1 为阻塞模式
SEGGER_RTT_ConfigUpBuffer(1, "DataOut", &abDataOut[0], sizeof(abDataOut),
                          SEGGER_RTT_MODE_BLOCK_IF_FIFO_FULL);
```

**补充**：缓冲区配置完成后，后续只应修改其 flags。

---

#### 7.3.3 `SEGGER_RTT_GetKey()`

从 RTT 缓冲区 0 读取一个字符（主机此前已写入数据）。

```c
int SEGGER_RTT_GetKey (void);
```

| 返回值 | 含义 |
| --- | --- |
| `>= 0` | 读取到的字符（0–255） |
| `< 0` | 无可用字符（缓冲区空） |

```c
int c;
c = SEGGER_RTT_GetKey();
if (c == 'q') {
  exit();
}
```

---

#### 7.3.4 `SEGGER_RTT_HasKey()`

检查 RTT 缓冲区中是否至少有一个可读字符。

```c
int SEGGER_RTT_HasKey (void);
```

| 返回值 | 含义 |
| --- | --- |
| `1` | 缓冲区中至少有一个字符 |
| `0` | 无字符可读 |

```c
if (SEGGER_RTT_HasKey()) {
  int c = SEGGER_RTT_GetKey();
}
```

---

#### 7.3.5 `SEGGER_RTT_Init()`

初始化 RTT 控制块。

```c
void SEGGER_RTT_Init (void);
```

**补充**

- 用于 RAM 目标时，应在应用启动时调用；
- 若 RTT 控制块被链接到**非 0 初始化**的 RAM 段，它**必须**是第一个被调用的 `SEGGER_RTT_*` 函数。

---

#### 7.3.6 `SEGGER_RTT_printf()`

向主机发送格式化字符串。

```c
int SEGGER_RTT_printf (unsigned BufferIndex, const char * sFormat, ...)
```

| 参数 | 含义 |
| --- | --- |
| `BufferIndex` | 要发送字符串的上行通道索引 |
| `sFormat` | 格式字符串指针，其后为转换用的参数 |

| 返回值 | 含义 |
| --- | --- |
| `>= 0` | 已发送的字节数 |
| `< 0` | 错误 |

**示例**

```c
SEGGER_RTT_printf(0, "SEGGER RTT Sample. Uptime: %.10dms.", /*OS_Time*/ 890912);
// 通道 0 上的格式化输出：SEGGER RTT Sample. Uptime: 890912ms.
```

**补充**

1. 转换规范语法：`%[flags][FieldWidth][.Precision]ConversionSpecifier`
   > 注意：除 `d`、`u`、`x` 外，其余说明符会忽略 Flags、FieldWidth 与 Precision。
2. 支持的 flags：
   | Flag | 含义 |
   | --- | --- |
   | `-` | 在字段宽度内左对齐 |
   | `+` | 对有符号转换总是打印符号 |
   | `0` | 用 0 而非空格填充。使用 `-` 标志或指定精度时忽略 |
3. 支持的转换说明符：
   | 说明符 | 含义 |
   | --- | --- |
   | `c` | 以单个字符打印参数 |
   | `d` | 以有符号整数打印参数 |
   | `u` | 以无符号整数打印参数 |
   | `x` | 以十六进制整数打印参数 |
   | `s` | 打印参数指向的字符串 |
   | `p` | 以 8 位十六进制整数打印参数（参数应为 `void*`） |

---

#### 7.3.7 `SEGGER_RTT_Read()`

从任一 RTT 下行通道读取主机先前存入的字符。

```c
unsigned SEGGER_RTT_Read (unsigned BufferIndex, char* pBuffer, unsigned BufferSize);
```

| 参数 | 含义 |
| --- | --- |
| `BufferIndex` | 要读取的下行通道索引 |
| `pBuffer` | 存放读出字符的缓冲区指针 |
| `BufferSize` | 缓冲区可用的字节数 |

**返回值**：`>= 0`，已读取的字节数。

```c
char acIn[4];
unsigned NumBytes = sizeof(acIn);
NumBytes = SEGGER_RTT_Read(0, &acIn[0], NumBytes);
if (NumBytes) {
  AnalyzeInput(acIn);
}
```

---

#### 7.3.8 `SEGGER_RTT_SetTerminal()`

设置「虚拟」终端，使通道 0 之后的数据发往该终端。

```c
void SEGGER_RTT_SetTerminal(char TerminalId);
```

| 参数 | 含义 |
| --- | --- |
| `TerminalId` | 虚拟终端 ID（0–9） |

```c
// 向用作错误输出的终端 1 发送字符串
SEGGER_RTT_SetTerminal(1);                          // 选择终端 1
SEGGER_RTT_WriteString(0, "ERROR: Buffer overflow");
SEGGER_RTT_SetTerminal(0);                          // 恢复标准终端
```

**补充**：此后经通道 0 发送的所有数据都会打印到所设终端，直到下次更改。

---

#### 7.3.9 `SEGGER_RTT_TerminalOut()`

向指定「虚拟」终端发送一个字符串。

```c
int SEGGER_RTT_TerminalOut (char TerminalID, const char* s);
```

| 参数 | 含义 |
| --- | --- |
| `TerminalId` | 虚拟终端 ID（0–9） |
| `s` | 待发送的、以 0 结尾的字符串指针 |

| 返回值 | 含义 |
| --- | --- |
| `>= 0` | 发送到终端的字节数 |
| `< 0` | 错误 |

```c
// 向终端 1 发送字符串，且不改变标准终端
SEGGER_RTT_TerminalOut(1, "ERROR: Buffer overflow.");
```

**补充**：`SEGGER_RTT_TerminalOut` **不影响**之后经通道 0 发送的数据。

---

#### 7.3.10 `SEGGER_RTT_Write()`

在某个 RTT 通道上向主机发送数据。

```c
unsigned SEGGER_RTT_Write (unsigned BufferIndex, const char* pBuffer, unsigned NumBytes);
```

| 参数 | 含义 |
| --- | --- |
| `BufferIndex` | 要发送数据的上行通道索引 |
| `pBuffer` | 待发送数据的指针 |
| `NumBytes` | 要发送的字节数 |

| 返回值 | 含义 |
| --- | --- |
| `>= 0` | 已发送的字节数 |
| `< 0` | 错误 |

**补充**：可发送**任意类型**的数据，不限于可打印字符。

---

#### 7.3.11 `SEGGER_RTT_WaitKey()`

等待直到 RTT 缓冲区 0 中至少有一个字符；一旦有字符可用即读取并返回。

```c
int SEGGER_RTT_WaitKey (void);
```

| 返回值 | 含义 |
| --- | --- |
| `>= 0` | 读取到的字符（0–255） |

```c
int c = 0;
do {
  c = SEGGER_RTT_WaitKey();
} while (c != 'c');
```

---

#### 7.3.12 `SEGGER_RTT_WriteString()`

经 RTT 向某上行通道写入一个以 0 结尾的字符串。

```c
unsigned SEGGER_RTT_WriteString (unsigned BufferIndex, const char* s);
```

| 参数 | 含义 |
| --- | --- |
| `BufferIndex` | 要发送字符串的上行通道索引 |
| `s` | 待发送的、以 0 结尾的字符串指针 |

**返回值**：`>= 0`，已发送的字节数。

```c
SEGGER_RTT_WriteString(0, "Hello World from your target.\n");
```

---

#### 7.3.13 `SEGGER_RTT_GetAvailWriteSpace()`

返回环形缓冲区中可用的字节数。

```c
unsigned SEGGER_RTT_GetAvailWriteSpace (unsigned BufferIndex);
```

| 参数 | 含义 |
| --- | --- |
| `BufferIndex` | 要检查空间的上行通道索引 |

**返回值**：`>= 0`，所选上行缓冲区中的空闲字节数。

```c
unsigned NumBytesFree;

NumBytesFree = SEGGER_RTT_GetAvailWriteSpace(0);
```

---

## 8. 配置宏

### 8.1 RTT 配置

| 宏 / 例程 | 含义 |
| --- | --- |
| `SEGGER_RTT_MAX_NUM_DOWN_BUFFERS` | 下行（到目标）通道的最大数量 |
| `SEGGER_RTT_MAX_NUM_UP_BUFFERS` | 上行（到主机）通道的最大数量 |
| `BUFFER_SIZE_DOWN` | 默认下行通道 0 的缓冲区大小 |
| `BUFFER_SIZE_UP` | 默认上行通道 0 的缓冲区大小 |
| `SEGGER_RTT_PRINT_BUFFER_SIZE` | `SEGGER_RTT_printf` 批量发送字符所用缓冲区大小 |
| `SEGGER_RTT_LOCK()` | 加锁例程，在 RTT 操作期间阻止中断与任务切换 |
| `SEGGER_RTT_UNLOCK()` | 解锁例程，RTT 操作结束后恢复中断与任务切换 |
| `SEGGER_RTT_IN_RAM` | 定义为 1 表示整个应用位于 RAM，避免在初始化段中误识别 RTT 控制块 |
| `SEGGER_RTT_SECTION` | （可选）链接 RTT 控制块的段名，可通过链接文件控制 CB 位置。默认（未定义）：若设置了 `SEGGER_RTT_BUFFER_SECTION` 则与之相同；否则无特定段 |
| `SEGGER_RTT_BUFFER_SECTION` | （可选）链接默认缓冲区的段名，可通过链接文件控制 CB 默认缓冲区位置。默认（未定义）：若设置了 `SEGGER_RTT_SECTION` 则与之相同；否则无特定段 |

### 8.2 通道缓冲区配置

| 宏 | 含义 |
| --- | --- |
| `SEGGER_RTT_MODE_BLOCK_IF_FIFO_FULL` | 上行缓冲区满时，写函数调用将阻塞 |
| `SEGGER_RTT_MODE_NO_BLOCK_SKIP` | 上行缓冲区空间不足以容纳全部输入数据时，**不写入任何数据** |
| `SEGGER_RTT_MODE_NO_BLOCK_TRIM` | 空间不足时，用输入数据填满可用空间，超出部分丢弃 |

> **注意**
> - `SEGGER_RTT_TerminalOut()` 保证隐式的终端切换命令总能发出，即使在非阻塞模式下也是如此。
> - 缓冲区配置**只影响目标设备侧缓冲区，不影响主机侧缓冲区**。

### 8.3 颜色控制序列

| 配置 | 含义 |
| --- | --- |
| `RTT_CTRL_RESET` | 重置文字颜色与背景色 |
| `RTT_CTRL_TEXT_*` | 设置文字颜色：`BLACK`、`RED`、`GREEN`、`YELLOW`、`BLUE`、`MAGENTA`、`CYAN`、`WHITE`（浅灰）、`BRIGHT_BLACK`（深灰）、`BRIGHT_RED`、`BRIGHT_GREEN`、`BRIGHT_YELLOW`、`BRIGHT_BLUE`、`BRIGHT_MAGENTA`、`BRIGHT_CYAN`、`BRIGHT_WHITE` |
| `RTT_CTRL_BG_*` | 设置背景色，可选颜色同上 |

---

## 9. 性能优化

当需要用 RTT 传输大量数据时，可采取以下措施提升性能：

- 升级到高端 J-Link 型号（如 J-Link PRO 或 J-Link ULTRA+），并使用更高的目标接口速度。
  > 注意：提高接口速度时务必保持在目标硬件的规格范围内。
- 增大目标侧的缓冲区大小。
- 将数据拆成多个小块写入，而不是一次性大批量写入。
- 尽可能避免额外的调试任务（如并行调试），因为它们优先级高于 RTT 后台任务。
- 确保 J-Link 与主机之间的连接（USB/以太网）稳定。

---

## 10. ARM Cortex 的背景内存访问

在 ARM Cortex 目标上，RTT 所需的背景内存访问通过所谓的 **AHB-AP** 完成。它类似 DMA，但仅供调试探头访问。

- Cortex-M 目标**始终存在** AHB-AP；
- Cortex-A / Cortex-R 上 AHB-AP 是**可选**组件，且可能实现多个 AP（有些甚至完全没有 AHB-AP）。

因此，要在 Cortex-A/R 上使用 RTT，需**手动指定**用于 RTT 背景内存访问的 AHB-AP 索引，通过 J-Link 命令字符串完成：`CORESIGHT_SetIndexAHBAPToUse`。

---

## 11. 示例代码

### 11.1 示例 main

```c
/**************************************************************
*                    SEGGER Microcontroller GmbH              *
*       Solutions for real time microcontroller applications  *
*            (c) 1995 - 2018 SEGGER Microcontroller GmbH      *
*      www.segger.com  Support: support@segger.com            *
--------------------------------------------------------------
File    : RTT.c
Purpose : Simple implementation for output via RTT.
          It can be used with any IDE.
---------------------------- END-OF-HEADER -------------------
*/

#include "SEGGER_RTT.h"

static void _Delay(int period) {
  int i = 100000 * period;
  do { ; } while (i--);
}

int main(void) {
  int Cnt = 0;

  SEGGER_RTT_Init();
  SEGGER_RTT_WriteString(0, "Hello World from SEGGER!\n");
  do {
    SEGGER_RTT_printf(0, "%sCounter: %s%d\n",
                      RTT_CTRL_TEXT_BRIGHT_WHITE,
                      RTT_CTRL_TEXT_BRIGHT_GREEN,
                      Cnt);
    if (Cnt > 100) {
      SEGGER_RTT_TerminalOut(1, RTT_CTRL_TEXT_BRIGHT_RED"Counter overflow!");
      Cnt = 0;
    }
    _Delay(100);
    Cnt++;
  } while (1);
  return 0;
}

/*************************** End of file ***************************/
```

### 11.2 示例向量表

```asm
_vectors:
        VECTOR __stack_end_
        VECTOR Reset_Handler
        ISR_HANDLER NMI_Handler
        VECTOR HardFault_Handler
        ISR_HANDLER MemManage_Handler
        ISR_HANDLER BusFault_Handler
        ISR_HANDLER UsageFault_Handler
        ISR_RESERVED
        .word (_SEGGER_RTT + 2)  // RTT 控制块地址，需 +2 才被标记为有效地址
        ISR_RESERVED
        ISR_RESERVED
        ISR_HANDLER SVC_Handler
        ISR_HANDLER DebugMon_Handler
        ISR_RESERVED
        ISR_HANDLER PendSV_Handler
        ISR_HANDLER SysTick_Handler
        //
        // 在此添加外部中断向量，例如：
        //   ISR_HANDLER ExternalISR0
        //   ISR_HANDLER ExternalISR1
        //   ISR_HANDLER ExternalISR2
        //   ISR_HANDLER ExternalISR3
        //

        .section .vectors, "a"
        .size _vectors, .-_vectors
_vectors_end:
```

---

## 12. 主机端通信

与目标上 RTT 实现的通信可由多种应用完成，甚至可借助 **J-Link SDK** 集成到自定义应用中。

目标侧使用 RTT 非常简单：实现代码可免费下载并集成到任意现有工程；任何 J-Link 都可用于 RTT 通信。

最简单的方式：在 J-Link 连接处于活动状态时（例如通过调试会话），用 Telnet 客户端或类似工具连接到 `localhost:19021`。此时可通过 SEGGER TELNET 配置字符串设置 RTT 通道，默认通道为通道 0（Terminal）。

J-Link 软件与文档包还附带一些更高级的应用，演示 RTT 的不同用途：

- J-Link RTT Viewer
- J-Link RTT Client
- J-Link RTT Logger

### 12.1 在主机应用中集成 RTT

任何 PC 应用（如调试器或数据可视化工具）都可以两种方式之一集成 RTT：

- 应用与 **RTT Telnet Server** 建立 socket 连接——当 J-Link 连接活动时该服务在 `localhost:19021` 上打开；
- 应用自行建立到 J-Link 的连接，使用 **J-Link SDK** 中的 J-Link RTT API 直接配置并使用 RTT。

---

## 13. J-Link 软件的 TELNET 通道

J-Link 软件在 localhost 端口（默认 **19021**）上提供类 TELNET 通道，便于与调试会话并行的第三方应用访问 RTT 数据。该通道使用非常简单：只需与 TELNET 端口建立 TCP/IP 连接，然后开始收发数据即可。详细信息参见「J-Link RTT TELNET Channel」。

---

## 14. 低功耗模式

若目标应用使用低功耗模式，RTT 可能无法按预期工作。使用 RTT 时，请确保**不使用**低功耗模式。J-Link 与低功耗模式的更多信息参见「J-Link Low-power mode debugging」。

---

## 15. 示例工程

- STM32F3 上的 RTT
- STM32F4 上的 RTT
- STM32H7 上的 RTT

---

## 16. 常见问题排查

若 RTT 无法正常工作，请依次检查：

- 确认目标器件**支持 RTT**（参见「运行模式」）；
- 确认使用**最新版本**的 J-Link 软件包（RTT 源码、`JLinkARM.dll`、RTT Viewer、RTT Client 等）；
- 确认目标应用为每个缓冲区使用了**正确的 RTT 模式**
  > 注意：除 `SEGGER_RTT_MODE_BLOCK_IF_FIFO_FULL` 外，任何模式在目标写入快于主机读取时都可能**丢失 RTT 数据**。
- 确认目标应用**未使用低功耗模式**；
- 确认 RTT 控制块位于 RAM 且可通过调试接口读取（RTT 缓冲区同样如此）；
- 确认主机侧**只有一个**应用在获取 RTT 数据。多个应用（如 RTT Viewer 与 RTT Client）并行运行时，会互相「抢」数据，导致 RTT 日志碎片化；
- 确认 J-Link DLL 能定位到 RTT 控制块：
  - 自动检测需要向 J-Link 传入**正确的目标器件名**（仅给内核名**不够**）；
    > 注意：许多器件在 J-Link DLL 中只定义了部分 RAM。若控制块位于该区域之外，自动检测**不会生效**，必须指定控制块地址或搜索范围。
  - 可用 J-Link 命令字符串设置控制块地址，或在 RTT Viewer 的配置对话框中设置；
  - 可用 J-Link 命令字符串设置搜索地址范围，或在 RTT Viewer 的配置对话框中设置；
- 确认目标应用使用的 RTT 通道正确（如 RTT Viewer 与 RTT Client **仅支持通道 0** 的数据通信）。

---

## 17. FAQ

**Q：J-Link 如何找到 RTT 缓冲区？**
A：有两种方式。若调试器（IDE）知道 SEGGER RTT 控制块的地址，可直接传给 J-Link（例如 J-Link Debugger 就是这么做的）。若使用的是不了解 SEGGER RTT 的其它应用，J-Link 会在应用运行期间于已知目标 RAM 中后台搜索该 ID。该过程通常只需零点几秒，不会延迟程序执行。

**Q：我在调试一个纯 RAM 应用，J-Link 找到了 RTT 缓冲区但没有输出，怎么办？**
A：若应用的初始化段存放在 RAM 中，J-Link 可能把初始化段里的块误识别为控制块，而非数据段中的真正控制块。将宏 `SEGGER_RTT_IN_RAM` 设为 1 即可避免。此后 J-Link 会找到正确的缓冲区，但需等到应用中第一次调用 SEGGER_RTT 函数之后。建议在应用开头调用 `SEGGER_RTT_Init()`。

**Q：能否用于没有 SWO 引脚的目标？**
A：可以。RTT 用的是调试接口——多数 Cortex-M 器件上的 JTAG 或 SWD（仅 2 线），某些瑞萨器件上的 FINE 接口，甚至英飞凌的 SPD 接口（单引脚！）。

**Q：能否用于 Cortex-M0 / M0+？**
A：可以。

**Q：一些 printf 类终端输出方案在脱离调试环境时会「崩溃」（它们使用软件断点，无调试器时触发 HardFault；或因为 SWO 未初始化而停机），导致调试版本无法独立运行。SEGGER RTT 呢？**
A：SEGGER RTT 默认使用非阻塞模式，即没有调试器、J-Link 甚至未连接时也不会暂停程序执行，应用会继续正常工作。

**Q：我的应用里 RTT 用法没问题，但看不到任何输出，怎么办？**
A：某些情况下 J-Link 无法在已知 RAM 区域内定位 RTT 缓冲区，此时可通过 J-Link exec 命令手动设置范围或确切地址：

- 设置搜索范围：`SetRTTSearchRanges <RangeStart [Hex]> <RangeSize>[, <Range1Start [Hex]> <Range1Size>, ...]`
  例：`SetRTTSearchRanges 0x10000000 0x1000, 0x2000000 0x1000`
- 设置缓冲区地址：`SetRTTAddr <RTTBufferAddress [Hex]>`
  例：`SetRTTAddr 0x20000000`
- 也可通过 J-Link Control Panel → RTTerminal 设置地址

> **注意**：J-Link exec 命令可在多数应用中执行，例如：
> - J-Link Commander：`exec <Command>`
> - J-Link GDB Server：`monitor exec <Command>`
> - IAR EW：在宏文件中调用 `__jlinkExecCommand("<Command>");`

---

*原文页面 ID：oldid=28386；译文中未逐字翻译的部分为图片说明、导航栏及重复性套话。*
