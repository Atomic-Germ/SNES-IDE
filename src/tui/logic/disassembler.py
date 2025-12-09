from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Set

# Import the complete opcode database
from .opcodes_complete import COMPLETE_OPCODES, InstructionInfo

@dataclass
class OpcodeMetadata:
    """Rich semantic metadata for an instruction."""
    mnemonic: str
    mode: str
    length: int
    flags_affected: Set[str] = field(default_factory=set)
    cycles_best: int = 1
    cycles_worst: int = 1
    description: str = ""

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
    flags_affected: Set[str] = field(default_factory=set)
    cycles_best: int = 1
    cycles_worst: int = 1
    description: str = ""
    references: List[int] = field(default_factory=list)

class Disassembler:
    # Use complete opcode database (all 256 instructions)
    # Built from opcodes_complete.py for comprehensive coverage
    OPCODE_META = {opcode: OpcodeMetadata(
        mnemonic=info.mnemonic,
        mode=info.addressing_mode,
        length=info.length,
        flags_affected=info.flags_affected,
        cycles_best=info.cycles_best,
        cycles_worst=info.cycles_worst,
        description=info.description
    ) for opcode, info in COMPLETE_OPCODES.items()}

    def __init__(self):
        self.m_flag = True  # Accumulator 8-bit
        self.x_flag = True  # Index 8-bit

    def disassemble(self, data: bytes, start_address: int = 0) -> List[DisassembledInstruction]:
        instructions = []
        pc = 0
        length = len(data)
        
        self.m_flag = True
        self.x_flag = True
        
        while pc < length:
            opcode = data[pc]
            meta = self.OPCODE_META.get(opcode)
            
            if not meta:
                # Unknown opcode
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
                
            mnemonic = meta.mnemonic
            mode = meta.mode
            default_len = meta.length
            current_len = default_len
            
            # Handle dynamic lengths based on processor flags
            if mode == "imm":
                if mnemonic in ["LDA", "STA", "ADC", "SBC", "CMP", "AND", "ORA", "EOR", "BIT"]:
                    if not self.m_flag:
                        current_len = 3
                elif mnemonic in ["LDX", "LDY", "CPX", "CPY"]:
                    if not self.x_flag:
                        current_len = 3
            
            # Check bounds
            if pc + current_len > length:
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
            
            # Generate semantic comment from metadata
            semantic_comment = self._generate_comment(mnemonic, meta, operands)
            
            # Track cross-references for branches
            references = []
            if mode in ["rel", "rl", "abs", "long"]:
                target = self._extract_target(operands, mode, start_address + pc)
                if target is not None:
                    references.append(target)
            
            # Update processor flags if REP/SEP
            if mnemonic == "REP":
                val = operands[0] if operands else 0
                if val & 0x20: self.m_flag = False
                if val & 0x10: self.x_flag = False
            elif mnemonic == "SEP":
                val = operands[0] if operands else 0
                if val & 0x20: self.m_flag = True
                if val & 0x10: self.x_flag = True
            
            instructions.append(DisassembledInstruction(
                address=start_address + pc,
                opcode=opcode,
                mnemonic=mnemonic,
                mode=mode,
                operands=operands,
                operand_text=operand_text,
                bytes_len=current_len,
                comment=semantic_comment,
                flags_affected=meta.flags_affected.copy(),
                cycles_best=meta.cycles_best,
                cycles_worst=meta.cycles_worst,
                description=meta.description,
                references=references
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
            offset = val
            if offset > 127:
                offset -= 256
            dest = current_pc + 2 + offset
            return f"${dest:04X}"
        elif mode == "rl":
            offset = val
            if offset > 32767:
                offset -= 65536
            dest = current_pc + 3 + offset
            return f"${dest:04X}"
            
        return f"${val:X}"

    def _generate_comment(self, mnemonic: str, meta: OpcodeMetadata, operands: bytes) -> str:
        """Generate semantic comment describing instruction purpose and effects."""
        parts = [meta.description]
        
        if meta.flags_affected:
            parts.append(f"[flags: {','.join(sorted(meta.flags_affected))}]")
        
        if meta.cycles_best != meta.cycles_worst:
            parts.append(f"[{meta.cycles_best}-{meta.cycles_worst} cycles]")
        else:
            parts.append(f"[{meta.cycles_best} cycles]")
        
        return " ".join(parts)

    def _extract_target(self, operands: bytes, mode: str, current_pc: int) -> Optional[int]:
        """Extract target address from operands for branch/jump instructions."""
        if len(operands) == 0:
            return None
            
        val = int.from_bytes(operands, 'little')
        
        if mode == "rel":
            offset = val if val <= 127 else val - 256
            return current_pc + 2 + offset
        elif mode == "rl":
            offset = val if val <= 32767 else val - 65536
            return current_pc + 3 + offset
        elif mode == "abs":
            return val
        elif mode == "long":
            return val
            
        return None
