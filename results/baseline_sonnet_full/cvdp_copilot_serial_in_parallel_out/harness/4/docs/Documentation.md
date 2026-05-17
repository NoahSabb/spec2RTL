# 8-bit Shift-Left Register with Positive-Edge Clock, Serial In, and Parallel Out #

This document describes the design and functionality of an 8-bit shift-left register implemented in Verilog. The module takes a serial input and provides a parallel output, shifting its contents left on each positive edge of the clock signal.

## SIPO (Serial In, and Parallel Out) Specification ##

Inputs
- **clock**: The clock signal that triggers the shift operation on its positive edge.
- **serial_in**: The serial input bit to be shifted into the register.

Output
- **parallel_out [7:0]**: An 8-bit parallel output representing the current state of the register.

## Signals Table for 8-bit Shift-Left Register ##

| **Signal Name** | **Direction** | **Width** | **Description**                         |
|-----------------|---------------|-----------|-----------------------------------------|
| clock           | Input         | 1 bit     | Clock signal that triggers the shift operation on its positive edge. |
| serial_in       | Input         | 1 bit     | Serial input bit to be shifted into the register. |
| parallel_out    | Output        | 8 bits    | 8-bit parallel output representing the current state of the register. |

## SIPO (Serial In, and Parallel Out) Specification Description ##
- **Clock Signal (`clock`)**: The register shifts its contents on the rising edge of this signal. The shift operation only occurs during the transition from low to high of the clock signal.
- **Serial Input (`serial_in`)**: This single-bit input is shifted into the least significant bit (LSB) of the register on each clock pulse.
- **Parallel Output (`parallel_out`)**: This is an 8-bit wide output that holds the current value of the register. It updates on each positive clock edge to reflect the shifted contents.

## SIPO (Serial In, and Parallel Out) Functional Overview ##
- On every positive edge of the clock signal, the register's contents are shifted one position to the left.
- The bit in `serial_in` is placed in the least significant bit position (`parallel_out[0]`).
- The most significant bit (`parallel_out[7]`) is discarded during the shift operation.
- The new value of the register is available at the parallel output (`parallel_out`).

