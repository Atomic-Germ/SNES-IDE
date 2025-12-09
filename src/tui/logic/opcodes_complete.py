"""
Complete 65816 opcode reference database.

This module provides comprehensive metadata for all 256 6502/65816 opcodes,
organized for easy lookup and expansion.

The intent is to provide a complete reference that can be integrated into
the disassembler to provide semantic information for every instruction.
"""

from dataclasses import dataclass
from typing import Set

@dataclass
class InstructionInfo:
    """Complete instruction metadata."""
    mnemonic: str
    addressing_mode: str
    length: int
    flags_affected: Set[str]
    cycles_best: int
    cycles_worst: int
    description: str
    notes: str = ""

# Complete 65816 instruction set reference
# Note: Some entries marked as "undocumented" or "reserved" in original 6502
# Format: 0xHH: InstructionInfo(...)

COMPLETE_OPCODES = {
    # 0x00-0x0F: Misc and BRK/ORA group
    0x00: InstructionInfo("BRK", "imp", 2, {"B", "I"}, 7, 7, "Break / Force Interrupt", "Sets B flag, pushes PC and flags"),
    0x01: InstructionInfo("ORA", "dp,x", 2, {"N", "Z"}, 6, 6, "OR with DP,X"),
    0x02: InstructionInfo("COP", "imm", 2, {"B", "I"}, 7, 7, "Coprocessor Interrupt", "65816 only"),
    0x03: InstructionInfo("ORA", "sr,s", 2, {"N", "Z"}, 4, 4, "OR with Stack Relative"),
    0x04: InstructionInfo("TSB", "dp", 2, {"N", "V", "Z"}, 5, 5, "Test and Set Bits"),
    0x05: InstructionInfo("ORA", "dp", 2, {"N", "Z"}, 3, 3, "OR with DP"),
    0x06: InstructionInfo("ASL", "dp", 2, {"N", "Z", "C"}, 5, 5, "Arithmetic Shift Left DP"),
    0x07: InstructionInfo("ORA", "dp,l", 2, {"N", "Z"}, 6, 6, "OR with DP Long"),
    0x08: InstructionInfo("PHP", "imp", 1, {}, 3, 3, "Push Processor Status"),
    0x09: InstructionInfo("ORA", "imm", 2, {"N", "Z"}, 2, 2, "OR Accumulator Immediate"),
    0x0A: InstructionInfo("ASL", "acc", 1, {"N", "Z", "C"}, 2, 2, "Arithmetic Shift Left Accumulator"),
    0x0B: InstructionInfo("PHD", "imp", 1, {}, 4, 4, "Push Direct Page Register", "65816 only"),
    0x0C: InstructionInfo("TSB", "abs", 3, {"N", "V", "Z"}, 6, 6, "Test and Set Bits Absolute"),
    0x0D: InstructionInfo("ORA", "abs", 3, {"N", "Z"}, 4, 4, "OR with Absolute"),
    0x0E: InstructionInfo("ASL", "abs", 3, {"N", "Z", "C"}, 6, 6, "Arithmetic Shift Left Absolute"),
    0x0F: InstructionInfo("ORA", "long", 4, {"N", "Z"}, 5, 5, "OR with Long Absolute"),

    # 0x10-0x1F: Branch and BIT group
    0x10: InstructionInfo("BPL", "rel", 2, {}, 2, 4, "Branch Plus (N=0)"),
    0x11: InstructionInfo("ORA", "dp,y", 2, {"N", "Z"}, 5, 5, "OR with DP,Y"),
    0x12: InstructionInfo("ORA", "dp", 2, {"N", "Z"}, 5, 5, "OR with DP Indirect"),
    0x13: InstructionInfo("ORA", "sr,s,y", 2, {"N", "Z"}, 4, 4, "OR Stack Relative Indirect"),
    0x14: InstructionInfo("TRB", "dp", 2, {"N", "V", "Z"}, 5, 5, "Test and Reset Bits"),
    0x15: InstructionInfo("ORA", "dp,x", 2, {"N", "Z"}, 4, 4, "OR with DP,X"),
    0x16: InstructionInfo("ASL", "dp,x", 2, {"N", "Z", "C"}, 6, 6, "Arithmetic Shift Left DP,X"),
    0x17: InstructionInfo("ORA", "dp,l,y", 2, {"N", "Z"}, 6, 6, "OR with DP Long,Y"),
    0x18: InstructionInfo("CLC", "imp", 1, {"C"}, 2, 2, "Clear Carry Flag"),
    0x19: InstructionInfo("ORA", "abs,y", 3, {"N", "Z"}, 4, 5, "OR with Absolute,Y"),
    0x1A: InstructionInfo("INC", "acc", 1, {"N", "Z"}, 2, 2, "Increment Accumulator", "65816 only"),
    0x1B: InstructionInfo("TCS", "imp", 1, {}, 2, 2, "Transfer Accumulator to Stack Ptr", "65816 only"),
    0x1C: InstructionInfo("TRB", "abs", 3, {"N", "V", "Z"}, 6, 6, "Test and Reset Bits Absolute"),
    0x1D: InstructionInfo("ORA", "abs,x", 3, {"N", "Z"}, 4, 5, "OR with Absolute,X"),
    0x1E: InstructionInfo("ASL", "abs,x", 3, {"N", "Z", "C"}, 7, 7, "Arithmetic Shift Left Absolute,X"),
    0x1F: InstructionInfo("ORA", "long,x", 4, {"N", "Z"}, 5, 5, "OR with Long,X"),

    # 0x20-0x2F: JSR and AND group
    0x20: InstructionInfo("JSR", "abs", 3, {}, 6, 6, "Jump Subroutine Absolute"),
    0x21: InstructionInfo("AND", "dp,x", 2, {"N", "Z"}, 6, 6, "AND with DP,X"),
    0x22: InstructionInfo("JSL", "long", 4, {}, 8, 8, "Jump Subroutine Long", "65816 only"),
    0x23: InstructionInfo("AND", "sr,s", 2, {"N", "Z"}, 4, 4, "AND with Stack Relative"),
    0x24: InstructionInfo("BIT", "dp", 2, {"N", "V", "Z"}, 3, 3, "Bit Test DP"),
    0x25: InstructionInfo("AND", "dp", 2, {"N", "Z"}, 3, 3, "AND with DP"),
    0x26: InstructionInfo("ROL", "dp", 2, {"N", "Z", "C"}, 5, 5, "Rotate Left DP"),
    0x27: InstructionInfo("AND", "dp,l", 2, {"N", "Z"}, 6, 6, "AND with DP Long"),
    0x28: InstructionInfo("PLP", "imp", 1, {}, 4, 4, "Pull Processor Status"),
    0x29: InstructionInfo("AND", "imm", 2, {"N", "Z"}, 2, 2, "AND Accumulator Immediate"),
    0x2A: InstructionInfo("ROL", "acc", 1, {"N", "Z", "C"}, 2, 2, "Rotate Left Accumulator"),
    0x2B: InstructionInfo("PLD", "imp", 1, {}, 5, 5, "Pull Direct Page Register", "65816 only"),
    0x2C: InstructionInfo("BIT", "abs", 3, {"N", "V", "Z"}, 4, 4, "Bit Test Absolute"),
    0x2D: InstructionInfo("AND", "abs", 3, {"N", "Z"}, 4, 4, "AND with Absolute"),
    0x2E: InstructionInfo("ROL", "abs", 3, {"N", "Z", "C"}, 6, 6, "Rotate Left Absolute"),
    0x2F: InstructionInfo("AND", "long", 4, {"N", "Z"}, 5, 5, "AND with Long Absolute"),

    # 0x30-0x3F: BMI and EOR group
    0x30: InstructionInfo("BMI", "rel", 2, {}, 2, 4, "Branch Minus (N=1)"),
    0x31: InstructionInfo("AND", "dp,y", 2, {"N", "Z"}, 5, 5, "AND with DP,Y"),
    0x32: InstructionInfo("AND", "dp", 2, {"N", "Z"}, 5, 5, "AND with DP Indirect"),
    0x33: InstructionInfo("AND", "sr,s,y", 2, {"N", "Z"}, 4, 4, "AND Stack Relative Indirect"),
    0x34: InstructionInfo("BIT", "dp,x", 2, {"N", "V", "Z"}, 4, 4, "Bit Test DP,X"),
    0x35: InstructionInfo("AND", "dp,x", 2, {"N", "Z"}, 4, 4, "AND with DP,X"),
    0x36: InstructionInfo("ROL", "dp,x", 2, {"N", "Z", "C"}, 6, 6, "Rotate Left DP,X"),
    0x37: InstructionInfo("AND", "dp,l,y", 2, {"N", "Z"}, 6, 6, "AND with DP Long,Y"),
    0x38: InstructionInfo("SEC", "imp", 1, {"C"}, 2, 2, "Set Carry Flag"),
    0x39: InstructionInfo("AND", "abs,y", 3, {"N", "Z"}, 4, 5, "AND with Absolute,Y"),
    0x3A: InstructionInfo("DEC", "acc", 1, {"N", "Z"}, 2, 2, "Decrement Accumulator", "65816 only"),
    0x3B: InstructionInfo("TSC", "imp", 1, {"N", "Z"}, 2, 2, "Transfer Stack Ptr to Accumulator", "65816 only"),
    0x3C: InstructionInfo("BIT", "abs,x", 3, {"N", "V", "Z"}, 4, 5, "Bit Test Absolute,X"),
    0x3D: InstructionInfo("AND", "abs,x", 3, {"N", "Z"}, 4, 5, "AND with Absolute,X"),
    0x3E: InstructionInfo("ROL", "abs,x", 3, {"N", "Z", "C"}, 7, 7, "Rotate Left Absolute,X"),
    0x3F: InstructionInfo("AND", "long,x", 4, {"N", "Z"}, 5, 5, "AND with Long,X"),

    # 0x40-0x4F: RTI and EOR group
    0x40: InstructionInfo("RTI", "imp", 1, {}, 6, 6, "Return from Interrupt"),
    0x41: InstructionInfo("EOR", "dp,x", 2, {"N", "Z"}, 6, 6, "XOR with DP,X"),
    0x42: InstructionInfo("WDM", "imm", 2, {}, 2, 2, "Reserved for Future Expansion", "65816 reserved"),
    0x43: InstructionInfo("EOR", "sr,s", 2, {"N", "Z"}, 4, 4, "XOR with Stack Relative"),
    0x44: InstructionInfo("MVP", "xyc", 3, {}, 7, 7, "Block Move Positive", "65816 only"),
    0x45: InstructionInfo("EOR", "dp", 2, {"N", "Z"}, 3, 3, "XOR with DP"),
    0x46: InstructionInfo("LSR", "dp", 2, {"N", "Z", "C"}, 5, 5, "Logical Shift Right DP"),
    0x47: InstructionInfo("EOR", "dp,l", 2, {"N", "Z"}, 6, 6, "XOR with DP Long"),
    0x48: InstructionInfo("PHA", "imp", 1, {}, 3, 3, "Push Accumulator"),
    0x49: InstructionInfo("EOR", "imm", 2, {"N", "Z"}, 2, 2, "XOR Accumulator Immediate"),
    0x4A: InstructionInfo("LSR", "acc", 1, {"N", "Z", "C"}, 2, 2, "Logical Shift Right Accumulator"),
    0x4B: InstructionInfo("PHK", "imp", 1, {}, 3, 3, "Push Program Bank Register", "65816 only"),
    0x4C: InstructionInfo("JMP", "abs", 3, {}, 3, 3, "Jump Absolute"),
    0x4D: InstructionInfo("EOR", "abs", 3, {"N", "Z"}, 4, 4, "XOR with Absolute"),
    0x4E: InstructionInfo("LSR", "abs", 3, {"N", "Z", "C"}, 6, 6, "Logical Shift Right Absolute"),
    0x4F: InstructionInfo("EOR", "long", 4, {"N", "Z"}, 5, 5, "XOR with Long Absolute"),

    # 0x50-0x5F: BVC and ADC group
    0x50: InstructionInfo("BVC", "rel", 2, {}, 2, 4, "Branch Overflow Clear (V=0)"),
    0x51: InstructionInfo("EOR", "dp,y", 2, {"N", "Z"}, 5, 5, "XOR with DP,Y"),
    0x52: InstructionInfo("EOR", "dp", 2, {"N", "Z"}, 5, 5, "XOR with DP Indirect"),
    0x53: InstructionInfo("EOR", "sr,s,y", 2, {"N", "Z"}, 4, 4, "XOR Stack Relative Indirect"),
    0x54: InstructionInfo("MVN", "xyc", 3, {}, 7, 7, "Block Move Negative", "65816 only"),
    0x55: InstructionInfo("EOR", "dp,x", 2, {"N", "Z"}, 4, 4, "XOR with DP,X"),
    0x56: InstructionInfo("LSR", "dp,x", 2, {"N", "Z", "C"}, 6, 6, "Logical Shift Right DP,X"),
    0x57: InstructionInfo("EOR", "dp,l,y", 2, {"N", "Z"}, 6, 6, "XOR with DP Long,Y"),
    0x58: InstructionInfo("CLI", "imp", 1, {"I"}, 2, 2, "Clear Interrupt Disable"),
    0x59: InstructionInfo("EOR", "abs,y", 3, {"N", "Z"}, 4, 5, "XOR with Absolute,Y"),
    0x5A: InstructionInfo("PHY", "imp", 1, {}, 3, 3, "Push Y Register", "65816 only"),
    0x5B: InstructionInfo("TCD", "imp", 1, {"N", "Z"}, 2, 2, "Transfer Accumulator to Direct Page", "65816 only"),
    0x5C: InstructionInfo("JMP", "long", 4, {}, 4, 4, "Jump Long Absolute", "65816 only"),
    0x5D: InstructionInfo("EOR", "abs,x", 3, {"N", "Z"}, 4, 5, "XOR with Absolute,X"),
    0x5E: InstructionInfo("LSR", "abs,x", 3, {"N", "Z", "C"}, 7, 7, "Logical Shift Right Absolute,X"),
    0x5F: InstructionInfo("EOR", "long,x", 4, {"N", "Z"}, 5, 5, "XOR with Long,X"),

    # 0x60-0x6F: RTS and ADC group
    0x60: InstructionInfo("RTS", "imp", 1, {}, 6, 6, "Return from Subroutine"),
    0x61: InstructionInfo("ADC", "dp,x", 2, {"N", "V", "Z", "C"}, 6, 6, "Add with Carry DP,X"),
    0x62: InstructionInfo("PER", "rel", 3, {}, 6, 6, "Push Effective Relative Address", "65816 only"),
    0x63: InstructionInfo("ADC", "sr,s", 2, {"N", "V", "Z", "C"}, 4, 4, "Add with Carry Stack Relative"),
    0x64: InstructionInfo("STZ", "dp", 2, {}, 3, 3, "Store Zero to DP"),
    0x65: InstructionInfo("ADC", "dp", 2, {"N", "V", "Z", "C"}, 3, 3, "Add with Carry DP"),
    0x66: InstructionInfo("ROR", "dp", 2, {"N", "Z", "C"}, 5, 5, "Rotate Right DP"),
    0x67: InstructionInfo("ADC", "dp,l", 2, {"N", "V", "Z", "C"}, 6, 6, "Add with Carry DP Long"),
    0x68: InstructionInfo("PLA", "imp", 1, {"N", "Z"}, 4, 4, "Pull Accumulator"),
    0x69: InstructionInfo("ADC", "imm", 2, {"N", "V", "Z", "C"}, 2, 2, "Add with Carry Immediate"),
    0x6A: InstructionInfo("ROR", "acc", 1, {"N", "Z", "C"}, 2, 2, "Rotate Right Accumulator"),
    0x6B: InstructionInfo("RTL", "imp", 1, {}, 6, 6, "Return from Subroutine Long", "65816 only"),
    0x6C: InstructionInfo("JMP", "abs,x", 3, {}, 5, 5, "Jump Absolute Indirect"),
    0x6D: InstructionInfo("ADC", "abs", 3, {"N", "V", "Z", "C"}, 4, 4, "Add with Carry Absolute"),
    0x6E: InstructionInfo("ROR", "abs", 3, {"N", "Z", "C"}, 6, 6, "Rotate Right Absolute"),
    0x6F: InstructionInfo("ADC", "long", 4, {"N", "V", "Z", "C"}, 5, 5, "Add with Carry Long Absolute"),

    # 0x70-0x7F: BVS and LDA group
    0x70: InstructionInfo("BVS", "rel", 2, {}, 2, 4, "Branch Overflow Set (V=1)"),
    0x71: InstructionInfo("ADC", "dp,y", 2, {"N", "V", "Z", "C"}, 5, 5, "Add with Carry DP,Y"),
    0x72: InstructionInfo("ADC", "dp", 2, {"N", "V", "Z", "C"}, 5, 5, "Add with Carry DP Indirect"),
    0x73: InstructionInfo("ADC", "sr,s,y", 2, {"N", "V", "Z", "C"}, 4, 4, "Add with Carry Stack Relative Indirect"),
    0x74: InstructionInfo("STZ", "dp,x", 2, {}, 4, 4, "Store Zero to DP,X"),
    0x75: InstructionInfo("ADC", "dp,x", 2, {"N", "V", "Z", "C"}, 4, 4, "Add with Carry DP,X"),
    0x76: InstructionInfo("ROR", "dp,x", 2, {"N", "Z", "C"}, 6, 6, "Rotate Right DP,X"),
    0x77: InstructionInfo("ADC", "dp,l,y", 2, {"N", "V", "Z", "C"}, 6, 6, "Add with Carry DP Long,Y"),
    0x78: InstructionInfo("SEI", "imp", 1, {"I"}, 2, 2, "Set Interrupt Disable"),
    0x79: InstructionInfo("ADC", "abs,y", 3, {"N", "V", "Z", "C"}, 4, 5, "Add with Carry Absolute,Y"),
    0x7A: InstructionInfo("PLY", "imp", 1, {"N", "Z"}, 4, 4, "Pull Y Register"),
    0x7B: InstructionInfo("TDC", "imp", 1, {"N", "Z"}, 2, 2, "Transfer Direct Page to Accumulator", "65816 only"),
    0x7C: InstructionInfo("JMP", "abs,x", 3, {}, 6, 6, "Jump Absolute Indirect,X", "65816 only"),
    0x7D: InstructionInfo("ADC", "abs,x", 3, {"N", "V", "Z", "C"}, 4, 5, "Add with Carry Absolute,X"),
    0x7E: InstructionInfo("ROR", "abs,x", 3, {"N", "Z", "C"}, 7, 7, "Rotate Right Absolute,X"),
    0x7F: InstructionInfo("ADC", "long,x", 4, {"N", "V", "Z", "C"}, 5, 5, "Add with Carry Long,X"),

    # 0x80-0x8F: BRA and STA group
    0x80: InstructionInfo("BRA", "rel", 2, {}, 3, 3, "Branch Always", "65816 only"),
    0x81: InstructionInfo("STA", "dp,x", 2, {}, 6, 6, "Store Accumulator DP,X"),
    0x82: InstructionInfo("BRL", "rl", 3, {}, 4, 4, "Branch Always Long", "65816 only"),
    0x83: InstructionInfo("STA", "sr,s", 2, {}, 4, 4, "Store Accumulator Stack Relative"),
    0x84: InstructionInfo("STY", "dp", 2, {}, 3, 3, "Store Y DP"),
    0x85: InstructionInfo("STA", "dp", 2, {}, 3, 3, "Store Accumulator DP"),
    0x86: InstructionInfo("STX", "dp", 2, {}, 3, 3, "Store X DP"),
    0x87: InstructionInfo("STA", "dp,l", 2, {}, 6, 6, "Store Accumulator DP Long"),
    0x88: InstructionInfo("DEY", "imp", 1, {"N", "Z"}, 2, 2, "Decrement Y"),
    0x89: InstructionInfo("BIT", "imm", 2, {"N", "V", "Z"}, 2, 2, "Bit Test Immediate", "65816 only"),
    0x8A: InstructionInfo("TXA", "imp", 1, {"N", "Z"}, 2, 2, "Transfer X to Accumulator"),
    0x8B: InstructionInfo("PHB", "imp", 1, {}, 3, 3, "Push Data Bank Register", "65816 only"),
    0x8C: InstructionInfo("STY", "abs", 3, {}, 4, 4, "Store Y Absolute"),
    0x8D: InstructionInfo("STA", "abs", 3, {}, 4, 4, "Store Accumulator Absolute"),
    0x8E: InstructionInfo("STX", "abs", 3, {}, 4, 4, "Store X Absolute"),
    0x8F: InstructionInfo("STA", "long", 4, {}, 5, 5, "Store Accumulator Long"),

    # 0x90-0x9F: BCC and LDY group
    0x90: InstructionInfo("BCC", "rel", 2, {}, 2, 4, "Branch Carry Clear (C=0)"),
    0x91: InstructionInfo("STA", "dp,y", 2, {}, 6, 6, "Store Accumulator DP,Y"),
    0x92: InstructionInfo("STA", "dp", 2, {}, 5, 5, "Store Accumulator DP Indirect"),
    0x93: InstructionInfo("STA", "sr,s,y", 2, {}, 4, 4, "Store Accumulator Stack Relative Indirect"),
    0x94: InstructionInfo("STY", "dp,x", 2, {}, 4, 4, "Store Y DP,X"),
    0x95: InstructionInfo("STA", "dp,x", 2, {}, 4, 4, "Store Accumulator DP,X"),
    0x96: InstructionInfo("STX", "dp,y", 2, {}, 4, 4, "Store X DP,Y"),
    0x97: InstructionInfo("STA", "dp,l,y", 2, {}, 6, 6, "Store Accumulator DP Long,Y"),
    0x98: InstructionInfo("TYA", "imp", 1, {"N", "Z"}, 2, 2, "Transfer Y to Accumulator"),
    0x99: InstructionInfo("STA", "abs,y", 3, {}, 5, 5, "Store Accumulator Absolute,Y"),
    0x9A: InstructionInfo("TXS", "imp", 1, {}, 2, 2, "Transfer X to Stack Pointer"),
    0x9B: InstructionInfo("TXY", "imp", 1, {"N", "Z"}, 2, 2, "Transfer X to Y", "65816 only"),
    0x9C: InstructionInfo("STZ", "abs", 3, {}, 4, 4, "Store Zero Absolute"),
    0x9D: InstructionInfo("STA", "abs,x", 3, {}, 5, 5, "Store Accumulator Absolute,X"),
    0x9E: InstructionInfo("STZ", "abs,x", 3, {}, 5, 5, "Store Zero Absolute,X"),
    0x9F: InstructionInfo("STA", "long,x", 4, {}, 5, 5, "Store Accumulator Long,X"),

    # 0xA0-0xAF: LDY and LDX group
    0xA0: InstructionInfo("LDY", "imm", 2, {"N", "Z"}, 2, 2, "Load Y Immediate"),
    0xA1: InstructionInfo("LDA", "dp,x", 2, {"N", "Z"}, 6, 6, "Load Accumulator DP,X"),
    0xA2: InstructionInfo("LDX", "imm", 2, {"N", "Z"}, 2, 2, "Load X Immediate"),
    0xA3: InstructionInfo("LDA", "sr,s", 2, {"N", "Z"}, 4, 4, "Load Accumulator Stack Relative"),
    0xA4: InstructionInfo("LDY", "dp", 2, {"N", "Z"}, 3, 3, "Load Y DP"),
    0xA5: InstructionInfo("LDA", "dp", 2, {"N", "Z"}, 3, 3, "Load Accumulator DP"),
    0xA6: InstructionInfo("LDX", "dp", 2, {"N", "Z"}, 3, 3, "Load X DP"),
    0xA7: InstructionInfo("LDA", "dp,l", 2, {"N", "Z"}, 6, 6, "Load Accumulator DP Long"),
    0xA8: InstructionInfo("TAY", "imp", 1, {"N", "Z"}, 2, 2, "Transfer Accumulator to Y"),
    0xA9: InstructionInfo("LDA", "imm", 2, {"N", "Z"}, 2, 2, "Load Accumulator Immediate"),
    0xAA: InstructionInfo("TAX", "imp", 1, {"N", "Z"}, 2, 2, "Transfer Accumulator to X"),
    0xAB: InstructionInfo("PLB", "imp", 1, {"N", "Z"}, 4, 4, "Pull Data Bank Register", "65816 only"),
    0xAC: InstructionInfo("LDY", "abs", 3, {"N", "Z"}, 4, 4, "Load Y Absolute"),
    0xAD: InstructionInfo("LDA", "abs", 3, {"N", "Z"}, 4, 4, "Load Accumulator Absolute"),
    0xAE: InstructionInfo("LDX", "abs", 3, {"N", "Z"}, 4, 4, "Load X Absolute"),
    0xAF: InstructionInfo("LDA", "long", 4, {"N", "Z"}, 5, 5, "Load Accumulator Long"),

    # 0xB0-0xBF: BCS and CPY group
    0xB0: InstructionInfo("BCS", "rel", 2, {}, 2, 4, "Branch Carry Set (C=1)"),
    0xB1: InstructionInfo("LDA", "dp,y", 2, {"N", "Z"}, 5, 5, "Load Accumulator DP,Y"),
    0xB2: InstructionInfo("LDA", "dp", 2, {"N", "Z"}, 5, 5, "Load Accumulator DP Indirect"),
    0xB3: InstructionInfo("LDA", "sr,s,y", 2, {"N", "Z"}, 4, 4, "Load Accumulator Stack Relative Indirect"),
    0xB4: InstructionInfo("LDY", "dp,x", 2, {"N", "Z"}, 4, 4, "Load Y DP,X"),
    0xB5: InstructionInfo("LDA", "dp,x", 2, {"N", "Z"}, 4, 4, "Load Accumulator DP,X"),
    0xB6: InstructionInfo("LDX", "dp,y", 2, {"N", "Z"}, 4, 4, "Load X DP,Y"),
    0xB7: InstructionInfo("LDA", "dp,l,y", 2, {"N", "Z"}, 6, 6, "Load Accumulator DP Long,Y"),
    0xB8: InstructionInfo("CLV", "imp", 1, {"V"}, 2, 2, "Clear Overflow Flag"),
    0xB9: InstructionInfo("LDA", "abs,y", 3, {"N", "Z"}, 4, 5, "Load Accumulator Absolute,Y"),
    0xBA: InstructionInfo("TSX", "imp", 1, {"N", "Z"}, 2, 2, "Transfer Stack Pointer to X"),
    0xBB: InstructionInfo("TYX", "imp", 1, {"N", "Z"}, 2, 2, "Transfer Y to X", "65816 only"),
    0xBC: InstructionInfo("LDY", "abs,x", 3, {"N", "Z"}, 4, 5, "Load Y Absolute,X"),
    0xBD: InstructionInfo("LDA", "abs,x", 3, {"N", "Z"}, 4, 5, "Load Accumulator Absolute,X"),
    0xBE: InstructionInfo("LDX", "abs,y", 3, {"N", "Z"}, 4, 5, "Load X Absolute,Y"),
    0xBF: InstructionInfo("LDA", "long,x", 4, {"N", "Z"}, 5, 5, "Load Accumulator Long,X"),

    # 0xC0-0xCF: CPY and CMP group
    0xC0: InstructionInfo("CPY", "imm", 2, {"N", "Z", "C"}, 2, 2, "Compare Y Immediate"),
    0xC1: InstructionInfo("CMP", "dp,x", 2, {"N", "Z", "C"}, 6, 6, "Compare DP,X"),
    0xC2: InstructionInfo("REP", "imm", 2, {"N", "V", "B", "D", "I", "Z", "C"}, 3, 3, "Reset Processor Status", "65816 only"),
    0xC3: InstructionInfo("CMP", "sr,s", 2, {"N", "Z", "C"}, 4, 4, "Compare Stack Relative"),
    0xC4: InstructionInfo("CPY", "dp", 2, {"N", "Z", "C"}, 3, 3, "Compare Y DP"),
    0xC5: InstructionInfo("CMP", "dp", 2, {"N", "Z", "C"}, 3, 3, "Compare DP"),
    0xC6: InstructionInfo("DEC", "dp", 2, {"N", "Z"}, 5, 5, "Decrement DP"),
    0xC7: InstructionInfo("CMP", "dp,l", 2, {"N", "Z", "C"}, 6, 6, "Compare DP Long"),
    0xC8: InstructionInfo("INY", "imp", 1, {"N", "Z"}, 2, 2, "Increment Y"),
    0xC9: InstructionInfo("CMP", "imm", 2, {"N", "Z", "C"}, 2, 2, "Compare Immediate"),
    0xCA: InstructionInfo("DEX", "imp", 1, {"N", "Z"}, 2, 2, "Decrement X"),
    0xCB: InstructionInfo("WAI", "imp", 1, {}, 3, 3, "Wait for Interrupt", "65816 only"),
    0xCC: InstructionInfo("CPY", "abs", 3, {"N", "Z", "C"}, 4, 4, "Compare Y Absolute"),
    0xCD: InstructionInfo("CMP", "abs", 3, {"N", "Z", "C"}, 4, 4, "Compare Absolute"),
    0xCE: InstructionInfo("DEC", "abs", 3, {"N", "Z"}, 6, 6, "Decrement Absolute"),
    0xCF: InstructionInfo("CMP", "long", 4, {"N", "Z", "C"}, 5, 5, "Compare Long Absolute"),

    # 0xD0-0xDF: BNE and SBC group
    0xD0: InstructionInfo("BNE", "rel", 2, {}, 2, 4, "Branch Not Equal (Z=0)"),
    0xD1: InstructionInfo("CMP", "dp,y", 2, {"N", "Z", "C"}, 5, 5, "Compare DP,Y"),
    0xD2: InstructionInfo("CMP", "dp", 2, {"N", "Z", "C"}, 5, 5, "Compare DP Indirect"),
    0xD3: InstructionInfo("CMP", "sr,s,y", 2, {"N", "Z", "C"}, 4, 4, "Compare Stack Relative Indirect"),
    0xD4: InstructionInfo("PEI", "dp", 2, {}, 6, 6, "Push Effective Indirect Address", "65816 only"),
    0xD5: InstructionInfo("CMP", "dp,x", 2, {"N", "Z", "C"}, 4, 4, "Compare DP,X"),
    0xD6: InstructionInfo("DEC", "dp,x", 2, {"N", "Z"}, 6, 6, "Decrement DP,X"),
    0xD7: InstructionInfo("CMP", "dp,l,y", 2, {"N", "Z", "C"}, 6, 6, "Compare DP Long,Y"),
    0xD8: InstructionInfo("CLD", "imp", 1, {"D"}, 2, 2, "Clear Decimal Mode"),
    0xD9: InstructionInfo("CMP", "abs,y", 3, {"N", "Z", "C"}, 4, 5, "Compare Absolute,Y"),
    0xDA: InstructionInfo("PHX", "imp", 1, {}, 3, 3, "Push X Register", "65816 only"),
    0xDB: InstructionInfo("STP", "imp", 1, {}, 3, 3, "Stop", "65816 only"),
    0xDC: InstructionInfo("JML", "abs", 3, {}, 6, 6, "Jump Indirect Long", "65816 only"),
    0xDD: InstructionInfo("CMP", "abs,x", 3, {"N", "Z", "C"}, 4, 5, "Compare Absolute,X"),
    0xDE: InstructionInfo("DEC", "abs,x", 3, {"N", "Z"}, 7, 7, "Decrement Absolute,X"),
    0xDF: InstructionInfo("CMP", "long,x", 4, {"N", "Z", "C"}, 5, 5, "Compare Long,X"),

    # 0xE0-0xEF: CPX and SBC group
    0xE0: InstructionInfo("CPX", "imm", 2, {"N", "Z", "C"}, 2, 2, "Compare X Immediate"),
    0xE1: InstructionInfo("SBC", "dp,x", 2, {"N", "V", "Z", "C"}, 6, 6, "Subtract with Carry DP,X"),
    0xE2: InstructionInfo("SEP", "imm", 2, {"N", "V", "B", "D", "I", "Z", "C"}, 3, 3, "Set Processor Status", "65816 only"),
    0xE3: InstructionInfo("SBC", "sr,s", 2, {"N", "V", "Z", "C"}, 4, 4, "Subtract with Carry Stack Relative"),
    0xE4: InstructionInfo("CPX", "dp", 2, {"N", "Z", "C"}, 3, 3, "Compare X DP"),
    0xE5: InstructionInfo("SBC", "dp", 2, {"N", "V", "Z", "C"}, 3, 3, "Subtract with Carry DP"),
    0xE6: InstructionInfo("INC", "dp", 2, {"N", "Z"}, 5, 5, "Increment DP"),
    0xE7: InstructionInfo("SBC", "dp,l", 2, {"N", "V", "Z", "C"}, 6, 6, "Subtract with Carry DP Long"),
    0xE8: InstructionInfo("INX", "imp", 1, {"N", "Z"}, 2, 2, "Increment X"),
    0xE9: InstructionInfo("SBC", "imm", 2, {"N", "V", "Z", "C"}, 2, 2, "Subtract with Carry Immediate"),
    0xEA: InstructionInfo("NOP", "imp", 1, {}, 2, 2, "No Operation"),
    0xEB: InstructionInfo("XBA", "imp", 1, {"N", "Z"}, 3, 3, "Exchange B and A Accumulators", "65816 only"),
    0xEC: InstructionInfo("CPX", "abs", 3, {"N", "Z", "C"}, 4, 4, "Compare X Absolute"),
    0xED: InstructionInfo("SBC", "abs", 3, {"N", "V", "Z", "C"}, 4, 4, "Subtract with Carry Absolute"),
    0xEE: InstructionInfo("INC", "abs", 3, {"N", "Z"}, 6, 6, "Increment Absolute"),
    0xEF: InstructionInfo("SBC", "long", 4, {"N", "V", "Z", "C"}, 5, 5, "Subtract with Carry Long Absolute"),

    # 0xF0-0xFF: BEQ and remaining group
    0xF0: InstructionInfo("BEQ", "rel", 2, {}, 2, 4, "Branch Equal (Z=1)"),
    0xF1: InstructionInfo("SBC", "dp,y", 2, {"N", "V", "Z", "C"}, 5, 5, "Subtract with Carry DP,Y"),
    0xF2: InstructionInfo("SBC", "dp", 2, {"N", "V", "Z", "C"}, 5, 5, "Subtract with Carry DP Indirect"),
    0xF3: InstructionInfo("SBC", "sr,s,y", 2, {"N", "V", "Z", "C"}, 4, 4, "Subtract with Carry Stack Relative Indirect"),
    0xF4: InstructionInfo("PEA", "abs", 3, {}, 5, 5, "Push Effective Absolute Address", "65816 only"),
    0xF5: InstructionInfo("SBC", "dp,x", 2, {"N", "V", "Z", "C"}, 4, 4, "Subtract with Carry DP,X"),
    0xF6: InstructionInfo("INC", "dp,x", 2, {"N", "Z"}, 6, 6, "Increment DP,X"),
    0xF7: InstructionInfo("SBC", "dp,l,y", 2, {"N", "V", "Z", "C"}, 6, 6, "Subtract with Carry DP Long,Y"),
    0xF8: InstructionInfo("SED", "imp", 1, {"D"}, 2, 2, "Set Decimal Mode"),
    0xF9: InstructionInfo("SBC", "abs,y", 3, {"N", "V", "Z", "C"}, 4, 5, "Subtract with Carry Absolute,Y"),
    0xFA: InstructionInfo("PLX", "imp", 1, {"N", "Z"}, 4, 4, "Pull X Register", "65816 only"),
    0xFB: InstructionInfo("XCE", "imp", 1, {"C"}, 2, 2, "Exchange Carry and Emulation Mode", "65816 only"),
    0xFC: InstructionInfo("JSR", "abs,x", 3, {}, 8, 8, "Jump Subroutine Absolute,X", "65816 only"),
    0xFD: InstructionInfo("SBC", "abs,x", 3, {"N", "V", "Z", "C"}, 4, 5, "Subtract with Carry Absolute,X"),
    0xFE: InstructionInfo("INC", "abs,x", 3, {"N", "Z"}, 7, 7, "Increment Absolute,X"),
    0xFF: InstructionInfo("SBC", "long,x", 4, {"N", "V", "Z", "C"}, 5, 5, "Subtract with Carry Long,X"),
}

def get_opcode_info(opcode: int) -> InstructionInfo:
    """Get instruction info for an opcode, with fallback to unknown."""
    if opcode in COMPLETE_OPCODES:
        return COMPLETE_OPCODES[opcode]
    else:
        return InstructionInfo(
            mnemonic="db",
            addressing_mode="imm",
            length=1,
            flags_affected=set(),
            cycles_best=0,
            cycles_worst=0,
            description="Unknown/Undefined Opcode",
            notes="Not in standard 65816 instruction set"
        )

if __name__ == "__main__":
    # Demo
    total = len(COMPLETE_OPCODES)
    print(f"Complete 65816 Opcode Database")
    print(f"Total opcodes documented: {total}/256")
    print(f"Coverage: {total/256*100:.1f}%")
    print(f"\nAll 256 opcodes are now comprehensively documented with:")
    print(f"  • Mnemonic and addressing mode")
    print(f"  • Instruction length")
    print(f"  • Processor flags affected")
    print(f"  • Cycle timing (best/worst case)")
    print(f"  • Human-readable description")
    print(f"  • Implementation notes (65816-specific, etc.)")
