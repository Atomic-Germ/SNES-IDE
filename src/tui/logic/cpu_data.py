# 65816 Opcode Database
# Format: Mnemonic -> { AddressingMode: { opcode, bytes, cycles, flags } }
# Simplified for the "Silicon Turtleneck" prototype

OPCODES = {
    "ADC": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....ZC"}, # +1 if m=0
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....ZC"}, # +1 if DL!=0
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....ZC"},
    },
    "AND": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....Z."},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....Z."},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....Z."},
    },
    "ASL": {
        "acc": {"bytes": 1, "cycles": 2, "flags": "N.....ZC"},
        "dp":  {"bytes": 2, "cycles": 5, "flags": "N.....ZC"},
        "abs": {"bytes": 3, "cycles": 6, "flags": "N.....ZC"},
    },
    "BCC": {"rel": {"bytes": 2, "cycles": 2, "flags": "........"}}, # +1 if branch taken, +1 if page cross
    "BCS": {"rel": {"bytes": 2, "cycles": 2, "flags": "........"}},
    "BEQ": {"rel": {"bytes": 2, "cycles": 2, "flags": "........"}},
    "BIT": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "......Z."},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "NV....Z."},
        "abs": {"bytes": 3, "cycles": 4, "flags": "NV....Z."},
    },
    "BMI": {"rel": {"bytes": 2, "cycles": 2, "flags": "........"}},
    "BNE": {"rel": {"bytes": 2, "cycles": 2, "flags": "........"}},
    "BPL": {"rel": {"bytes": 2, "cycles": 2, "flags": "........"}},
    "BRA": {"rel": {"bytes": 2, "cycles": 3, "flags": "........"}},
    "BRK": {"imp": {"bytes": 2, "cycles": 7, "flags": "....DI.."}},
    "BRL": {"rl":  {"bytes": 3, "cycles": 4, "flags": "........"}},
    "BVC": {"rel": {"bytes": 2, "cycles": 2, "flags": "........"}},
    "BVS": {"rel": {"bytes": 2, "cycles": 2, "flags": "........"}},
    "CLC": {"imp": {"bytes": 1, "cycles": 2, "flags": ".......0"}},
    "CLD": {"imp": {"bytes": 1, "cycles": 2, "flags": "....0..."}},
    "CLI": {"imp": {"bytes": 1, "cycles": 2, "flags": ".....0.."}},
    "CLV": {"imp": {"bytes": 1, "cycles": 2, "flags": ".0......"}},
    "CMP": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....ZC"},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....ZC"},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....ZC"},
    },
    "CPX": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....ZC"},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....ZC"},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....ZC"},
    },
    "CPY": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....ZC"},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....ZC"},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....ZC"},
    },
    "DEC": {
        "acc": {"bytes": 1, "cycles": 2, "flags": "N.....Z."},
        "dp":  {"bytes": 2, "cycles": 5, "flags": "N.....Z."},
        "abs": {"bytes": 3, "cycles": 6, "flags": "N.....Z."},
    },
    "DEX": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "DEY": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "EOR": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....Z."},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....Z."},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....Z."},
    },
    "INC": {
        "acc": {"bytes": 1, "cycles": 2, "flags": "N.....Z."},
        "dp":  {"bytes": 2, "cycles": 5, "flags": "N.....Z."},
        "abs": {"bytes": 3, "cycles": 6, "flags": "N.....Z."},
    },
    "INX": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "INY": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "JMP": {
        "abs": {"bytes": 3, "cycles": 3, "flags": "........"},
        "ind": {"bytes": 3, "cycles": 5, "flags": "........"},
        "lng": {"bytes": 4, "cycles": 4, "flags": "........"}, # JML
    },
    "JSL": {"lng": {"bytes": 4, "cycles": 8, "flags": "........"}},
    "JSR": {
        "abs": {"bytes": 3, "cycles": 6, "flags": "........"},
        "ind": {"bytes": 3, "cycles": 6, "flags": "........"}, # JSR (abs,x)
    },
    "LDA": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....Z."},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....Z."},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....Z."},
        "lng": {"bytes": 4, "cycles": 5, "flags": "N.....Z."},
    },
    "LDX": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....Z."},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....Z."},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....Z."},
    },
    "LDY": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....Z."},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....Z."},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....Z."},
    },
    "LSR": {
        "acc": {"bytes": 1, "cycles": 2, "flags": "0.....ZC"},
        "dp":  {"bytes": 2, "cycles": 5, "flags": "0.....ZC"},
        "abs": {"bytes": 3, "cycles": 6, "flags": "0.....ZC"},
    },
    "MVN": {"mvc": {"bytes": 3, "cycles": 7, "flags": "........"}}, # +7 per byte
    "MVP": {"mvc": {"bytes": 3, "cycles": 7, "flags": "........"}},
    "NOP": {"imp": {"bytes": 1, "cycles": 2, "flags": "........"}},
    "ORA": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N.....Z."},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N.....Z."},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N.....Z."},
    },
    "PEA": {"stk": {"bytes": 3, "cycles": 5, "flags": "........"}},
    "PEI": {"stk": {"bytes": 2, "cycles": 6, "flags": "........"}},
    "PER": {"stk": {"bytes": 3, "cycles": 6, "flags": "........"}},
    "PHA": {"stk": {"bytes": 1, "cycles": 3, "flags": "........"}},
    "PHB": {"stk": {"bytes": 1, "cycles": 3, "flags": "........"}},
    "PHD": {"stk": {"bytes": 1, "cycles": 4, "flags": "........"}},
    "PHK": {"stk": {"bytes": 1, "cycles": 3, "flags": "........"}},
    "PHP": {"stk": {"bytes": 1, "cycles": 3, "flags": "........"}},
    "PHX": {"stk": {"bytes": 1, "cycles": 3, "flags": "........"}},
    "PHY": {"stk": {"bytes": 1, "cycles": 3, "flags": "........"}},
    "PLA": {"stk": {"bytes": 1, "cycles": 4, "flags": "N.....Z."}},
    "PLB": {"stk": {"bytes": 1, "cycles": 4, "flags": "N.....Z."}},
    "PLD": {"stk": {"bytes": 1, "cycles": 5, "flags": "N.....Z."}},
    "PLP": {"stk": {"bytes": 1, "cycles": 4, "flags": "NVMXDIZC"}},
    "PLX": {"stk": {"bytes": 1, "cycles": 4, "flags": "N.....Z."}},
    "PLY": {"stk": {"bytes": 1, "cycles": 4, "flags": "N.....Z."}},
    "REP": {"imm": {"bytes": 2, "cycles": 3, "flags": "NVMXDIZC"}},
    "ROL": {
        "acc": {"bytes": 1, "cycles": 2, "flags": "N.....ZC"},
        "dp":  {"bytes": 2, "cycles": 5, "flags": "N.....ZC"},
        "abs": {"bytes": 3, "cycles": 6, "flags": "N.....ZC"},
    },
    "ROR": {
        "acc": {"bytes": 1, "cycles": 2, "flags": "N.....ZC"},
        "dp":  {"bytes": 2, "cycles": 5, "flags": "N.....ZC"},
        "abs": {"bytes": 3, "cycles": 6, "flags": "N.....ZC"},
    },
    "RTI": {"stk": {"bytes": 1, "cycles": 6, "flags": "NVMXDIZC"}},
    "RTL": {"stk": {"bytes": 1, "cycles": 6, "flags": "........"}},
    "RTS": {"stk": {"bytes": 1, "cycles": 6, "flags": "........"}},
    "SBC": {
        "imm": {"bytes": 2, "cycles": 2, "flags": "N...V.ZC"},
        "dp":  {"bytes": 2, "cycles": 3, "flags": "N...V.ZC"},
        "abs": {"bytes": 3, "cycles": 4, "flags": "N...V.ZC"},
    },
    "SEC": {"imp": {"bytes": 1, "cycles": 2, "flags": ".......1"}},
    "SED": {"imp": {"bytes": 1, "cycles": 2, "flags": "....1..."}},
    "SEI": {"imp": {"bytes": 1, "cycles": 2, "flags": ".....1.."}},
    "SEP": {"imm": {"bytes": 2, "cycles": 3, "flags": "NVMXDIZC"}},
    "STA": {
        "dp":  {"bytes": 2, "cycles": 3, "flags": "........"},
        "abs": {"bytes": 3, "cycles": 4, "flags": "........"},
        "lng": {"bytes": 4, "cycles": 5, "flags": "........"},
    },
    "STP": {"imp": {"bytes": 1, "cycles": 3, "flags": "........"}}, # Stop processor
    "STX": {
        "dp":  {"bytes": 2, "cycles": 3, "flags": "........"},
        "abs": {"bytes": 3, "cycles": 4, "flags": "........"},
    },
    "STY": {
        "dp":  {"bytes": 2, "cycles": 3, "flags": "........"},
        "abs": {"bytes": 3, "cycles": 4, "flags": "........"},
    },
    "STZ": {
        "dp":  {"bytes": 2, "cycles": 3, "flags": "........"},
        "abs": {"bytes": 3, "cycles": 4, "flags": "........"},
    },
    "TAX": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "TAY": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "TCD": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "TCS": {"imp": {"bytes": 1, "cycles": 2, "flags": "........"}},
    "TDC": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "TRB": {
        "dp":  {"bytes": 2, "cycles": 5, "flags": "......Z."},
        "abs": {"bytes": 3, "cycles": 6, "flags": "......Z."},
    },
    "TSB": {
        "dp":  {"bytes": 2, "cycles": 5, "flags": "......Z."},
        "abs": {"bytes": 3, "cycles": 6, "flags": "......Z."},
    },
    "TSC": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "TSX": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "TXA": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "TXS": {"imp": {"bytes": 1, "cycles": 2, "flags": "........"}},
    "TXY": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "TYA": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "TYX": {"imp": {"bytes": 1, "cycles": 2, "flags": "N.....Z."}},
    "WAI": {"imp": {"bytes": 1, "cycles": 3, "flags": "........"}}, # Wait for interrupt
    "XBA": {"imp": {"bytes": 1, "cycles": 3, "flags": "N.....Z."}},
    "XCE": {"imp": {"bytes": 1, "cycles": 2, "flags": ".......C"}}, # Exchange Carry/Emulation
}
