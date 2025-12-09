"""
SDK Templates for new SNES projects.

Provides starter code and configuration templates for each supported SDK.
"""

from enum import Enum
from pathlib import Path
from typing import Dict


class SDK(str, Enum):
    """Supported SNES SDKs"""
    PVSNESLIB = "pvsneslib"
    DOTNETSNES = "dotnetsnes"
    JAVASNES = "javasnes"


class ROMType(str, Enum):
    """SNES ROM types"""
    LOROM = "lorom"
    HIROM = "hirom"
    EXLOROM = "exlorom"
    EXHIROM = "exhirom"


# Template files for each SDK
TEMPLATES: Dict[str, Dict[str, str]] = {
    SDK.PVSNESLIB: {
        "src/main.c": '''#include <snes.h>

int main() {
    // Initialize the console
    consoleInit();
    
    // Clear the screen
    consoleNormalPrint(CONSOLE_COLOR_WHITE, CONSOLE_COLOR_BLACK, 0, 0, "Hello, SNES!");
    
    // Main game loop
    while(1) {
        // Update display
        WaitForVBlank();
    }
    
    return 0;
}
''',
        "src/startup.asm": '''; SNES startup code for PVSnesLib
.include "hdr.asm"
.bank 0
.org 0

; Reset vector
.dw $0000          ; Native COP
.dw $0000          ; Native BRK
.dw $0000          ; Native ABORT
.dw main           ; Native NMI (non-maskable interrupt)
.dw $0000          ; Native XIRQ
.dw main           ; Emulation Mode IRQ

; Emulation mode vectors
.org $FFF4
.dw $0000          ; COP
.dw main           ; ABORT
.dw main           ; NMI (vblank)
.dw main           ; RESET
.dw $0000          ; XIRQ (not used)
.dw main           ; IRQ
''',
        "assets/.gitkeep": "",
        "Makefile": '''CC = wla-dx
AS = wla-dx
LD = wlalink
CFLAGS = -Wall -std=c99
ASFLAGS = -v -W
LDFLAGS = 

TARGET = game
SOURCES = src/main.c
OBJECTS = build/main.o build/startup.o
OUTPUT = dist/$(TARGET).sfc

all: $(OUTPUT)

$(OUTPUT): $(OBJECTS)
\t$(LD) $(LDFLAGS) -o $@ link.script $(OBJECTS)

build/%.o: src/%.c
\t$(CC) $(CFLAGS) -c $< -o $@

build/%.o: src/%.asm
\t$(AS) $(ASFLAGS) -c $< -o $@

clean:
\trm -rf build/ dist/

.PHONY: all clean
''',
    },
    
    SDK.DOTNETSNES: {
        "src/Program.cs": '''using System;
using DotnetSnes;

class Program {
    static void Main() {
        // Initialize the console
        Console.WriteLine("Hello, SNES!");
        
        // Game loop
        while (true) {
            // Update display
            Console.ReadKey();
        }
    }
}
''',
        "src/snes.csproj": '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net6.0</TargetFramework>
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="DotnetSnes" Version="1.0.0" />
  </ItemGroup>
</Project>
''',
        "assets/.gitkeep": "",
    },
    
    SDK.JAVASNES: {
        "src/Game.java": '''import javasnes.SNES;

public class Game {
    public static void main(String[] args) {
        SNES console = new SNES();
        console.init();
        console.println("Hello, SNES!");
        
        // Game loop
        while (true) {
            console.update();
        }
    }
}
''',
        "src/pom.xml": '''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.snes</groupId>
    <artifactId>game</artifactId>
    <version>0.1.0</version>

    <dependencies>
        <dependency>
            <groupId>javasnes</groupId>
            <artifactId>javasnes</artifactId>
            <version>1.0.0</version>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.8.1</version>
                <configuration>
                    <source>11</source>
                    <target>11</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
''',
        "assets/.gitkeep": "",
    },
}


def get_project_template(sdk: SDK) -> Dict[str, str]:
    """Get the file templates for a given SDK"""
    return TEMPLATES.get(sdk, {})


def create_project_structure(project_dir: Path, sdk: SDK) -> None:
    """Create the basic directory structure for a new project"""
    
    # Core directories
    (project_dir / "src").mkdir(parents=True, exist_ok=True)
    (project_dir / "assets").mkdir(parents=True, exist_ok=True)
    (project_dir / "build").mkdir(parents=True, exist_ok=True)
    (project_dir / "dist").mkdir(parents=True, exist_ok=True)
    
    # Create SDK-specific template files
    templates = get_project_template(sdk)
    for file_path, content in templates.items():
        full_path = project_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)


def create_gitignore(project_dir: Path) -> None:
    """Create a .gitignore file for the project"""
    gitignore = project_dir / ".gitignore"
    gitignore.write_text('''# Build artifacts
build/
dist/
*.o
*.a
*.sfc
*.smc

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Python
__pycache__/
*.py[cod]
*$py.class
.Python
.venv/
venv/

# OS
.DS_Store
Thumbs.db

# Dependencies
node_modules/
.gradle/
target/
.m2/
''')


def create_readme(project_dir: Path, project_name: str, sdk: SDK) -> None:
    """Create a README for the project"""
    readme = project_dir / "README.md"
    readme.write_text(f'''# {project_name}

A SNES game project using {sdk.value.upper()}.

## Build

```bash
python -m src.tui.app
Press Ctrl+B to open the build system
Click Load Config, then Build
```

## Project Structure

- `src/` - Source code
- `assets/` - Graphics, audio, and other assets
- `build/` - Build artifacts (generated)
- `dist/` - Final ROM output (generated)

## SDK Documentation

See the {sdk.value} documentation for more information.
''')
