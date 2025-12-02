# 16K Page Size Patches

This directory contains patches for systems with 16K page sizes.

## Affected Systems

- Apple Silicon Macs running Asahi Linux
- Some ARM64 Linux distributions
- Custom kernels with 16K pages

## Detection

The Tool Manager detects 16K page systems via:
```bash
getconf PAGESIZE  # Returns 16384 instead of 4096
```

## Current Patches

Patches will be added here as issues are discovered and fixed.

### Expected Issues

Tools likely to need patches:

1. **LakeSnes** - Simple emulator, may need minor mmap alignment fixes
2. **bsnes** - Complex JIT, significant patching may be needed
3. **PVSnesLib/tcc** - 816-tcc compiler may have alignment assumptions

### Placeholder

Create subdirectories per tool:
```
16k-pagesize/
├── lakesnes/
│   └── mmap-alignment.patch
├── bsnes/
│   └── jit-pagesize.patch
└── pvsneslib/
    └── tcc-alignment.patch
```

## Testing

To verify a patch works:

1. Build on a 16K page system without patch - observe failure
2. Apply patch
3. Build again - should succeed
4. Run basic functionality tests
