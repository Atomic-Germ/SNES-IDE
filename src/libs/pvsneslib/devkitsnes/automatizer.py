# ...existing code...
try:
    from platform_bin import platform_bin_name
except Exception:
    # Fallback if the top-level import path isn't available in some run contexts
    def platform_bin_name(name):
        import platform as _platform
        return name if _platform.system().lower() == 'windows' else (name[:-4] if name.endswith('.exe') else name)

# ...existing code...
        self.cc = self.devkit_dir / 'bin' / platform_bin_name('816-tcc.exe')
        self.assembler = self.devkit_dir / 'bin' / platform_bin_name('wla-65816.exe')
        self.linker = self.devkit_dir / 'bin' / platform_bin_name('wlalink.exe')
        self.opt = self.tools_dir / platform_bin_name('816-opt.exe')
        self.ctf = self.tools_dir / platform_bin_name('constify.exe')
# ...existing code...