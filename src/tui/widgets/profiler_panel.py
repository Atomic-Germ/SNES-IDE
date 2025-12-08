from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Label, TextArea, DataTable, ProgressBar
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from src.tui.logic.profiler import Profiler, InstructionProfile

class ProfilerStats(Static):
    cycles = reactive(0)
    bytes = reactive(0)
    
    # NTSC V-Blank is approx 262 scanlines total, 224 visible.
    # 38 lines of V-Blank * 1364 master cycles / 8 (fast ROM) = ~6500 cycles?
    # Actually, standard "safe" V-Blank DMA budget is often cited around 6KB transfer.
    # For CPU logic in V-Blank, let's set a conservative "Tight" budget.
    # Scanline = 1364 master cycles. CPU runs at 3.58MHz (fast) or 2.68MHz (slow).
    # Let's assume FastROM (3.58MHz).
    # 1 CPU cycle ~= 6-8 master cycles.
    # 38 scanlines * 1364 / 8 = ~6479 CPU cycles.
    # Let's use 6000 as the "Full V-Blank" budget.
    VBLANK_BUDGET = 6000

    def compose(self) -> ComposeResult:
        yield Label("Total Cycles: 0", id="lbl-cycles")
        yield Label("Total Bytes: 0", id="lbl-bytes")
        yield Label("V-Blank Usage:", classes="header")
        yield ProgressBar(total=self.VBLANK_BUDGET, show_eta=False, id="pb-vblank")
        yield Label("0%", id="lbl-percent")

    def watch_cycles(self, val: int):
        try:
            self.query_one("#lbl-cycles", Label).update(f"Total Cycles: {val}")
            pb = self.query_one("#pb-vblank", ProgressBar)
            pb.progress = val
            
            percent = (val / self.VBLANK_BUDGET) * 100
            self.query_one("#lbl-percent", Label).update(f"{percent:.1f}% of V-Blank")
            
            if percent > 100:
                pb.styles.color = "red"
            elif percent > 80:
                pb.styles.color = "yellow"
            else:
                pb.styles.color = "green"
        except:
            pass

    def watch_bytes(self, val: int):
        try:
            self.query_one("#lbl-bytes", Label).update(f"Total Bytes: {val}")
        except:
            pass

class ProfilerPanel(Container):
    DEFAULT_CSS = """
    ProfilerPanel {
        layout: horizontal;
        height: 100%;
    }
    #left-col {
        width: 1fr;
        height: 100%;
    }
    #right-col {
        width: 40;
        height: 100%;
        padding: 1;
    }
    #asm-input {
        height: 50%;
        border: solid $primary;
    }
    #profile-table {
        height: 50%;
        border: solid $secondary;
    }
    ProfilerStats {
        height: auto;
        background: $surface;
        padding: 1;
        border: solid $accent;
    }
    """

    def __init__(self):
        super().__init__()
        self.profiler = Profiler()

    def compose(self) -> ComposeResult:
        with Vertical(id="left-col"):
            yield Label("Assembly Input (Paste Code Here)", classes="header")
            yield TextArea(id="asm-input", language="asm")
            yield Label("Cycle Breakdown", classes="header")
            yield DataTable(id="profile-table")
        
        with Vertical(id="right-col"):
            yield Label("The Silicon Turtleneck", classes="title")
            yield ProfilerStats(id="stats")
            yield Label("\nOpcode Reference", classes="header")
            yield TextArea(id="opcode-ref", read_only=True)

    def on_mount(self):
        table = self.query_one("#profile-table", DataTable)
        table.add_columns("Line", "Mnemonic", "Mode", "Cycles", "Bytes", "Flags")
        
        # Initial text
        self.query_one("#asm-input", TextArea).text = """
; Example V-Blank Routine
LDA #$80     ; Force V-Blank
STA $2100
LDA #$00     ; Sprite Address
STA $2102
STA $2103
LDX #$0000
loop:
LDA $7F0000, X  ; Copy OAM data
STA $2104
INX
CPX #$0220      ; 544 bytes
BNE loop
LDA #$0F     ; Screen On
STA $2100
        """.strip()
        
        self.update_profile()

    def on_text_area_changed(self, event: TextArea.Changed):
        if event.text_area.id == "asm-input":
            self.update_profile()

    def update_profile(self):
        code = self.query_one("#asm-input", TextArea).text
        profiles = self.profiler.profile_code(code)
        
        table = self.query_one("#profile-table", DataTable)
        table.clear()
        
        total_cycles = 0
        total_bytes = 0
        
        for p in profiles:
            total_cycles += p.cycles
            total_bytes += p.bytes
            
            # Highlight expensive instructions
            cycle_style = "red" if p.cycles > 6 else "green"
            
            table.add_row(
                str(p.line_num),
                p.mnemonic,
                p.mode,
                Text(str(p.cycles), style=cycle_style),
                str(p.bytes),
                p.flags
            )
            
        stats = self.query_one("#stats", ProfilerStats)
        stats.cycles = total_cycles
        stats.bytes = total_bytes
