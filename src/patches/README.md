# SNES-IDE Mini Patches

This directory contains patches for building tools from source on non-standard systems.

## Directory Structure

```
patches/
├── 16k-pagesize/           # Patches for 16K page size systems (Asahi Linux)
│   ├── lakesnes/
│   │   └── *.patch
│   ├── pvsneslib/
│   │   └── *.patch
│   └── bsnes/
│       └── *.patch
├── aarch64/                # ARM64-specific patches
└── asahi/                  # Asahi Linux specific patches
```

## How Patches Work

1. The Tool Manager detects system characteristics (page size, architecture, etc.)
2. When building a tool, it checks if any patches apply
3. Patches are applied using `patch -p1` before building

## Creating New Patches

To create a patch:

1. Clone the original source
2. Make your changes
3. Generate a diff:
   ```bash
   diff -u original_file modified_file > toolname/fix_description.patch
   ```

Or use git:
   ```bash
   git diff > toolname/fix_description.patch
   ```

## 16K Page Size Issues

Systems with 16K pages (like Asahi Linux on Apple Silicon) may have issues with:

- Memory-mapped allocations assuming 4K alignment
- JIT compilers with hardcoded page assumptions
- mmap() calls without proper alignment

Common fixes:
- Add `-DPAGE_SIZE=16384` to CFLAGS
- Use `posix_memalign()` instead of `malloc()` for aligned buffers
- Ensure mmap regions are 16K aligned

## Testing Patches

Before submitting a patch:

1. Build the tool without the patch (verify it fails or has issues)
2. Apply the patch
3. Build again (verify success)
4. Test the built tool functions correctly

## Contributing Patches

If you create patches for additional tools or systems:

1. Test thoroughly on the target system
2. Document what the patch fixes
3. Submit a pull request with:
   - The patch file(s)
   - Updated tools_mini.json if needed
   - Description of the issue and fix
