from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class DisassembledInstruction:
    address: int
    opcode: int
    mnemonic: str
    mode: str
    operands: bytes
    operand_text: str
    bytes_len: int
    comment: str = ""

class Disassembler:
    # Opcode Map: Opcode -> (Mnemonic, Mode, Length)
    # Length 0 means variable/unknown (or handle separately)
    # Modes: imp, imm, dp, abs, rel, etc.
    OPCODE_MAP = {
        0x00: ("BRK", "imp", 2),
        0x01: ("ORA", "dp,x", 2),
        0x02: ("COP", "imm", 2),
        0x03: ("ORA", "sr,s", 2),
        0x04: ("TSB", "dp", 2),
        0x05: ("ORA", "dp", 2),
        0x06: ("ASL", "dp", 2),
        0x07: ("ORA", "dp,l", 2),
        0x08: ("PHP", "imp", 1),
        0x09: ("ORA", "imm", 2), # M flag dependent
        0x0A: ("ASL", "acc", 1),
        0x0B: ("PHD", "imp", 1),
        0x0C: ("TSB", "abs", 3),
        0x0D: ("ORA", "abs", 3),
        0x0E: ("ASL", "abs", 3),
        0x0F: ("ORA", "long", 4),
        
        0x10: ("BPL", "rel", 2),
        0x18: ("CLC", "imp", 1),
        0x1B: ("TCS", "imp", 1),
        
        0x20: ("JSR", "abs", 3),
        0x22: ("JSL", "long", 4),
        0x29: ("AND", "imm", 2),
        
        0x38: ("SEC", "imp", 1),
        0x3A: ("DEC", "acc", 1),
        
        0x40: ("RTI", "imp", 1),
        0x42: ("WDM", "imm", 2),
        0x48: ("PHA", "imp", 1),
        0x4C: ("JMP", "abs", 3),
        
        0x5C: ("JMP", "long", 4),
        
        0x60: ("RTS", "imp", 1),
        0x64: ("STZ", "dp", 2),
        0x69: ("ADC", "imm", 2),
        0x6B: ("RTL", "imp", 1),
        
        0x78: ("SEI", "imp", 1),
        0x7A: ("PLY", "imp", 1),
        
        0x80: ("BRA", "rel", 2),
        0x82: ("BRL", "rl", 3),
        0x85: ("STA", "dp", 2),
        0x8D: ("STA", "abs", 3),
        0x8F: ("STA", "long", 4),
        
        0x9C: ("STZ", "abs", 3),
        0x9E: ("STZ", "abs,x", 3),
        
        0xA0: ("LDY", "imm", 2), # X flag dependent
        0xA2: ("LDX", "imm", 2), # X flag dependent
        0xA5: ("LDA", "dp", 2),
        0xA9: ("LDA", "imm", 2), # M flag dependent
        0xAD: ("LDA", "abs", 3),
        0xAF: ("LDA", "long", 4),
        
        0xC2: ("REP", "imm", 2),
        0xE2: ("SEP", "imm", 2),
        
        0xEA: ("NOP", "imp", 1),
        0xEB: ("XBA", "imp", 1),
        
        0xF0: ("BEQ", "rel", 2),
        0xFB: ("XCE", "imp", 1),
        0xFF: ("SBC", "long,x", 4),
    }

    def __init__(self):
        self.m_flag = True  # Accumulator 8-bit
        self.x_flag = True  # Index 8-bit

    def disassemble(self, data: bytes, start_address: int = 0) -> List[DisassembledInstruction]:
        instructions = []
        pc = 0
        length = len(data)
        
        # Reset flags for new disassembly (assume reset state or standard entry)
        # In a real flow tracer, we'd track these per instruction.
        self.m_flag = True
        self.x_flag = True
        
        while pc < length:
            opcode = data[pc]
            info = self.OPCODE_MAP.get(opcode)
            
            if not info:
                # Unknown opcode, treat as byte
                instructions.append(DisassembledInstruction(
                    address=start_address + pc,
                    opcode=opcode,
                    mnemonic="db",
                    mode="imm",
                    operands=bytes([opcode]),
                    operand_text=f"${opcode:02X}",
                    bytes_len=1,
                    comment="Unknown Opcode"
                ))
                pc += 1
                continue
                
            mnemonic, mode, default_len = info
            
            # Handle dynamic lengths based on flags (REP/SEP/M/X)
            # This is tricky in a linear sweep without flow analysis.
            # For now, we'll do a simple heuristic or stick to default.
            # REP/SEP change flags.
            
            current_len = default_len
            
            # Check for immediate mode size changes
            if mode == "imm":
                if mnemonic in ["LDA", "LDA", "STA", "ADC", "SBC", "CMP", "AND", "ORA", "EOR", "BIT"]:
                    if not self.m_flag: # 16-bit
                        current_len = 3
                elif mnemonic in ["LDX", "LDY", "CPX", "CPY"]:
                    if not self.x_flag: # 16-bit
                        current_len = 3
            
            # Ensure we have enough data
            if pc + current_len > length:
                # Partial instruction
                instructions.append(DisassembledInstruction(
                    address=start_address + pc,
                    opcode=opcode,
                    mnemonic="db",
                    mode="imm",
                    operands=data[pc:],
                    operand_text=f"${opcode:02X}...",
                    bytes_len=length - pc,
                    comment="Incomplete"
                ))
                break
                
            operands = data[pc+1 : pc+current_len]
            operand_text = self._format_operands(operands, mode, start_address + pc)
            
            # Update flags if REP/SEP
            if mnemonic == "REP":
                val = operands[0]
                if val & 0x20: self.m_flag = False
                if val & 0x10: self.x_flag = False
            elif mnemonic == "SEP":
                val = operands[0]
                if val & 0x20: self.m_flag = True
                if val & 0x10: self.x_flag = True
            
            instructions.append(DisassembledInstruction(
                address=start_address + pc,
                opcode=opcode,
                mnemonic=mnemonic,
                mode=mode,
                operands=operands,
                operand_text=operand_text,
                bytes_len=current_len
            ))
            
            pc += current_len
            
        return instructions

    def _format_operands(self, operands: bytes, mode: str, current_pc: int) -> str:
        if not operands:
            return ""
            
        val = 0
        for i, b in enumerate(operands):
            val |= b << (i * 8)
            
        if mode == "imm":
            if len(operands) == 1:
                return f"#${val:02X}"
            else:
                return f"#${val:04X}"
        elif mode == "dp":
            return f"${val:02X}"
        elif mode == "abs":
            return f"${val:04X}"
        elif mode == "long":
            return f"${val:06X}"
        elif mode == "rel":
            # Relative branch
            offset = val
            if offset > 127:
                offset -= 256
            dest = current_pc + 2 + offset
            return f"${dest:04X}" # Show absolute target
        elif mode == "rl":
            # Relative long
            offset = val
            if offset > 32767:
                offset -= 65536
            dest = current_pc + 3 + offset
            return f"${dest:04X}"
            
        return f"${val:X}"
