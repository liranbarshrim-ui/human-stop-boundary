"""Optional Linux process hardening for the privileged DAR dispatcher.

Defense-in-depth only; the seccomp configuration is deliberately a deny-list.
"""
import ctypes,ctypes.util,errno,os
class HardeningUnavailable(RuntimeError): pass
_LIB=None
def _load():
    global _LIB
    if _LIB is not None: return _LIB
    path=ctypes.util.find_library('seccomp')
    if not path: raise HardeningUnavailable('libseccomp not found')
    lib=ctypes.CDLL(path,use_errno=True)
    lib.seccomp_init.argtypes=[ctypes.c_uint32]; lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]; lib.seccomp_rule_add.restype=ctypes.c_int
    lib.seccomp_load.argtypes=[ctypes.c_void_p]; lib.seccomp_load.restype=ctypes.c_int
    lib.seccomp_release.argtypes=[ctypes.c_void_p]; lib.seccomp_release.restype=None
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p]; lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    _LIB=lib; return lib
def install_dispatcher_seccomp():
    if os.name!='posix' or not os.path.exists('/proc/self/status'): raise HardeningUnavailable('Linux required')
    lib=_load(); allow=0x7FFF0000; err=lambda e:0x00050000|(e&0xFFFF); ctx=lib.seccomp_init(allow)
    if not ctx: raise OSError(ctypes.get_errno(),'seccomp_init failed')
    blocked=['execve','execveat','fork','vfork','clone','clone3','ptrace','mount','umount2','pivot_root','setns','unshare','init_module','finit_module','delete_module','kexec_load','kexec_file_load','reboot','swapon','swapoff','socket','socketpair','connect','bind','listen']
    try:
        for name in blocked:
            nr=lib.seccomp_syscall_resolve_name(name.encode())
            if nr<0: continue
            rc=lib.seccomp_rule_add(ctx,err(errno.EPERM),nr,0)
            if rc!=0: raise OSError(rc,f'seccomp_rule_add failed for {name}')
        rc=lib.seccomp_load(ctx)
        if rc!=0: raise OSError(rc,'seccomp_load failed')
    finally: lib.seccomp_release(ctx)
def install_no_new_privs():
    libc=ctypes.CDLL(None,use_errno=True); libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong]; libc.prctl.restype=ctypes.c_int
    if libc.prctl(38,1,0,0,0)!=0: raise OSError(ctypes.get_errno(),'PR_SET_NO_NEW_PRIVS failed')
_LANDLOCK_CREATE_RULESET=444; _LANDLOCK_ADD_RULE=445; _LANDLOCK_RESTRICT_SELF=446; _LANDLOCK_RULE_PATH_BENEATH=1
_LL_ACCESS_FS_EXECUTE=1<<0; _LL_ACCESS_FS_WRITE_FILE=1<<1; _LL_ACCESS_FS_READ_FILE=1<<2; _LL_ACCESS_FS_READ_DIR=1<<3; _LL_ACCESS_FS_REMOVE_DIR=1<<4; _LL_ACCESS_FS_REMOVE_FILE=1<<5; _LL_ACCESS_FS_MAKE_CHAR=1<<6; _LL_ACCESS_FS_MAKE_DIR=1<<7; _LL_ACCESS_FS_MAKE_REG=1<<8; _LL_ACCESS_FS_MAKE_SOCK=1<<9; _LL_ACCESS_FS_MAKE_FIFO=1<<10; _LL_ACCESS_FS_MAKE_BLOCK=1<<11; _LL_ACCESS_FS_MAKE_SYM=1<<12; _LL_ACCESS_FS_REFER=1<<13; _LL_ACCESS_FS_TRUNCATE=1<<14
class _RulesetAttr(ctypes.Structure): _fields_=[('handled_access_fs',ctypes.c_uint64)]
class _PathBeneath(ctypes.Structure): _fields_=[('parent_fd',ctypes.c_int),('allowed_access',ctypes.c_uint64)]
def install_landlock(effect_root,state_dir):
    if os.uname().machine!='x86_64': raise HardeningUnavailable('Landlock policy currently implemented for x86_64')
    libc=ctypes.CDLL(None,use_errno=True); libc.syscall.restype=ctypes.c_long
    handled=sum(1<<i for i in range(15)); fd=libc.syscall(_LANDLOCK_CREATE_RULESET,ctypes.byref(_RulesetAttr(handled)),ctypes.sizeof(_RulesetAttr),0)
    if fd<0: raise OSError(ctypes.get_errno(),'landlock_create_ruleset failed')
    try:
        state_access=(_LL_ACCESS_FS_READ_FILE|_LL_ACCESS_FS_READ_DIR|_LL_ACCESS_FS_WRITE_FILE|_LL_ACCESS_FS_REMOVE_FILE|_LL_ACCESS_FS_REMOVE_DIR|_LL_ACCESS_FS_MAKE_REG|_LL_ACCESS_FS_MAKE_DIR|_LL_ACCESS_FS_REFER|_LL_ACCESS_FS_TRUNCATE)
        effect_access=(_LL_ACCESS_FS_READ_FILE|_LL_ACCESS_FS_READ_DIR|_LL_ACCESS_FS_WRITE_FILE|_LL_ACCESS_FS_MAKE_REG|_LL_ACCESS_FS_MAKE_DIR|_LL_ACCESS_FS_REFER|_LL_ACCESS_FS_TRUNCATE)
        for path,access in ((state_dir,state_access),(effect_root,effect_access)):
            pfd=os.open(os.path.realpath(path),os.O_PATH|os.O_DIRECTORY)
            try:
                rule=_PathBeneath(pfd,access); rc=libc.syscall(_LANDLOCK_ADD_RULE,fd,_LANDLOCK_RULE_PATH_BENEATH,ctypes.byref(rule),0)
                if rc<0: raise OSError(ctypes.get_errno(),f'landlock_add_rule failed for {path}')
            finally: os.close(pfd)
        if libc.syscall(_LANDLOCK_RESTRICT_SELF,fd,0,0,0)<0: raise OSError(ctypes.get_errno(),'landlock_restrict_self failed')
    finally: os.close(fd)
