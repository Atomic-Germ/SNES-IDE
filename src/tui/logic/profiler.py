import re
from dataclasses import dataclass
from typing import List, Dict, Optional
from .cpu_data import OPCODES

@dataclass
class InstructionProfile:
    line_num: int
    text: str
    mnemonic: str
    mode: str
    cycles: int
    bytes: int
    flags: str
    error: Optional[str] = None

class Profiler:
    def __init__(self):
        pass

    def profile_code(self, code: str) -> List[InstructionProfile]:
        profiles = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Remove comments
            if ';' in line:
                line = line.split(';')[0].strip()
            
            if not line:
                continue
                
            # Skip labels (ending in :)
            if line.endswith(':'):
                continue
                
            # Parse mnemonic and operand
            parts = line.split(None, 1)
            mnemonic = parts[0].upper()
            operand = parts[1] if len(parts) > 1 else ""
            
            profile = self._analyze_instruction(i + 1, line, mnemonic, operand)
            profiles.append(profile)
            
        return profiles

    def _analyze_instruction(self, line_num: int, text: str, mnemonic: str, operand: str) -> InstructionProfile:
        if mnemonic not in OPCODES:
            return InstructionProfile(line_num, text, mnemonic, "???", 0, 0, "????????", "Unknown Opcode")
            
        variants = OPCODES[mnemonic]
        
        # Guess addressing mode
        mode = self._guess_mode(mnemonic, operand, variants)
        
        if mode in variants:
            data = variants[mode]
            return InstructionProfile(
                line_num, 
                text, 
                mnemonic, 
                mode, 
                data["cycles"], 
                data["bytes"], 
                data["flags"]
            )
        else:
            # Fallback: return the first variant found (usually 'abs' or 'imp')
            # or try to find a 'default' one
            fallback_mode = next(iter(variants))
            data = variants[fallback_mode]
            return InstructionProfile(
                line_num, 
                text, 
                mnemonic, 
                f"{mode}?", 
                data["cycles"], 
                data["bytes"], 
                data["flags"],
                f"Mode mismatch (guessed {mode}, used {fallback_mode})"
            )

    def _guess_mode(self, mnemonic: str, operand: str, variants: Dict) -> str:
        operand = operand.strip()
        
        # Implicit / Accumulator / Stack
        if not operand:
            if "imp" in variants: return "imp"
            if "acc" in variants: return "acc" # ASL A -> ASL
            if "stk" in variants: return "stk"
            return "imp" # Default
            
        if operand.upper() == "A":
            return "acc"
            
        # Immediate
        if operand.startswith("#"):
            return "imm"
            
        # Indirect
        if operand.startswith("(") and operand.endswith(")"):
            return "ind"
            
        # Long Indirect
        if operand.startswith("[") and operand.endswith("]"):
            return "il"
            
        # Hex values
        # Remove modifiers like <, >, !
        clean_op = operand.replace("<", "").replace(">", "").replace("!", "")
        
        if "$" in clean_op:
            # Extract hex part
            try:
                hex_str = re.search(r'\$([0-9A-Fa-f]+)', clean_op)
                if hex_str:
                    val_len = len(hex_str.group(1))
                    if val_len <= 2:
                        if "dp" in variants: return "dp"
                        if "rel" in variants: return "rel" # Branch to offset
                    elif val_len <= 4:
                        if "abs" in variants: return "abs"
                        if "rel" in variants: return "rel" # Branch to label
                    else:
                        if "lng" in variants: return "lng"
            except:
                pass
                
        # Labels (assume Absolute or Relative depending on instruction type)
        if "rel" in variants: return "rel"
        if "abs" in variants: return "abs"
        if "lng" in variants: return "lng"
        
        return "abs" # Default fallback
