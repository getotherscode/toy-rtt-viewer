# toy-rtt-viewer
study rtt theory and do my rtt viewer

## theory
first of all, i need to figure out the layer

| layer       | do what |
| ---         | ---     |
|application  |RTT-viewer|
|communication|CMSIS-DAP/J-Link private protocol/ST-Link private protocol|
|debug-access |SW-DP/JTAG-DP/MEM-DP|
|physical     |SWD/JTAG|
|target       |mcu/ram/flash/periphral|

if i want to do a rtt-viewer, i need to figure out the procotol, but private protocol is not considered.
so, i need to study CMSIS-DAP, the public on, and use the daplink to acheive my goal.
here is the five part diagram.

```
Python 
     │
     │ USB / CMSIS-DAP
     ▼
CMSIS-DAP 
     │
     │ SWD
     ▼
SW-DP（Debug Port）
     │
     │ APACC
     ▼
MEM-AP（Memory Access Port）
     │
     │ AHB 
     ▼
STM32 RAM / Flash / Peripheral Register
```

## my targets
I will split my goal into five parts.

### Phase1：Python can recognize debugger and send CMSIS-DAP commands
```
CMSIS-DAP protocol

Python ↔ USB ↔ CMSIS-DAP Debug Probe
- USB HID / WinUSB

USB HID: standard human interface device, cross os platform
WinUSB: only windows

CMSIS-DAP V1: hidapi -> Windows HID Driver -> USB Interrupt IN / OUT
CMSIS-DAP V2: PyUSB -> WinUSB Driver -> USB Bulk IN/OUT

- CMSIS-DAP command format、Command ID、response format
ref: https://arm-software.github.io/CMSIS-DAP/latest

Protocol: 
Host -> Debug uint: CMD + Parameter (variable length)
Debug uint -> Host: CMD + Response (variable length)

- DAP_Info、DAP_Connect、DAP_Disconnect
- DAP_Transfer、DAP_TransferBlock
- SWJ_Sequence、DAP_SWJ_Clock
```

### Phase2：understand how CMSIS-DAP convert register access to SWD communication
```
SW-DP：study SWD physical communication

Debug Probe ↔ Target MCU
- SWDIO / SWCLK singal wire
- SWD request pack
- ACK：OK / WAIT / FAULT
- DP register：IDCODE、CTRL/STAT、SELECT、RDBUFF
- WAIT retry、FAULT clear、read pipeline
```

### Phase3：Python could read target MCU any memory address
```
MEM-AP：memory access
- DP & AP 
- APSEL / APBANKSEL
- MEM-AP  CSW、TAR、DRW
- AHB-AP / MEM-AP
- 32-bit memory read and write、address increasement
- AP access and DP RDBUFF pipeline mechanism
```

### Phase4：could read RTT log from MCU
```
RTT memory protocol
- RTT Control Block
- Up Buffer / Down Buffer
- Ring Buffer R/W pointer
- RTT control block location
- get MCU RAM log continuously
```

### Phase5: final toy RTT Viewer
```
Python viewer app
- USB device enumeration and communication
- CMSIS-DAP command encapsulation
- DP / AP / Memory API
- RTT automatically discover and data extraction 
- real time log shower、time stamp、terminal output
```