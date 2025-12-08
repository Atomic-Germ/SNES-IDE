from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, Label, DataTable, Button
from textual.reactive import reactive
from rich.text import Text

from src.tui.logic.disassembler import Disassembler

class DisassemblerPanel(Container):
    DEFAULT_CSS = """
    DisassemblerPanel {
        height: 100%;
        width: 100%;
    }
    #disasm-table {
        height: 1fr;
        border: solid $secondary;
    }
    #status-bar {
        height: 1;
        background: $surface;
        color: $text-muted;
    }
    """

    def __init__(self):
        super().__init__()
        self.disassembler = Disassembler()
        self.current_data = b""
        self.start_address = 0

    def compose(self) -> ComposeResult:
        yield Label("Disassembler", classes="header")
        yield DataTable(id="disasm-table")
        yield Label("Ready", id="status-bar")

    def on_mount(self):
        table = self.query_one("#disasm-table", DataTable)
        table.add_columns("Addr", "Hex", "Mnemonic", "Operands", "Comment")
        table.cursor_type = "row"

    def load_data(self, data: bytes, address: int = 0):
        self.current_data = data
        self.start_address = address
        self.refresh_disassembly()

    def refresh_disassembly(self):
        table = self.query_one("#disasm-table", DataTable)
        table.clear()
        
        if not self.current_data:
            return

        instructions = self.disassembler.disassemble(self.current_data, self.start_address)
        
        for instr in instructions:
            # Format Hex
            hex_str = f"{instr.opcode:02X} " + " ".join(f"{b:02X}" for b in instr.operands)
            
            # Add row
            table.add_row(
                f"${instr.address:04X}",
                hex_str,
                instr.mnemonic,
                instr.operand_text,
                instr.comment
            )
            
        self.query_one("#status-bar", Label).update(f"Disassembled {len(instructions)} instructions from ${self.start_address:04X}")

