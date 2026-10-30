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
so, i need to study CMSIS-DAP, the public one
