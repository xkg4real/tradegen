"""Windows directory pins for the explicit research-revocation anchor writer.

This independent stdlib implementation imports no execution or signer modules.
Only the explicit context opens Win32 handles. Existing compliance home and all
ancestors are pinned before the two fixed children are created, one at a time.
The pins deny write and delete sharing: deny-delete alone does not exclude a
writable handle used for FSCTL_SET_REPARSE_POINT. Unsupported native identity or
path semantics refuse; there is no lstat-only fallback. This is not a sandbox
against arbitrary same-process code or a Windows power-loss durability claim.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import ntpath
import os
from pathlib import Path, PureWindowsPath
import re

_REFUSED = 'RESEARCH_ANCHOR_WINDOWS_PIN_REFUSED'
_UNSUPPORTED = 'RESEARCH_ANCHOR_WINDOWS_PIN_UNSUPPORTED'
_DRIVE = re.compile(r'[A-Za-z]:')
_DIRECTORY = 0x10
_REFUSED_ATTRIBUTES = 0x400 | 0x1000 | 0x00040000 | 0x00400000
_MAX_CHARS = 32767


class RevocationPathError(ValueError):
    """Fixed diagnostics; no owner path or native exception text."""


def _need(condition, code=_REFUSED):
    if not condition:
        raise RevocationPathError(code)


def _lexical_path(value):
    _need(type(value) is str and 0 < len(value) <= _MAX_CHARS and '\x00' not in value)
    normalized = value.replace('/', '\\')
    drive, root, tail = ntpath.splitroot(normalized)
    _need(_DRIVE.fullmatch(drive) is not None and root == '\\')
    parts = tail.split('\\') if tail else []
    _need(all(part and part not in ('.', '..') and not ntpath.isreserved(part) for part in parts))
    return drive.upper() + root + '\\'.join(parts)


def _final_path(value):
    _need(type(value) is str and value.startswith('\\\\?\\'))
    return _lexical_path(value[4:])


@dataclass(frozen=True, kw_only=True)
class DirectoryInformation:
    attributes: int
    volume_serial: int
    file_index: int

    @property
    def identity(self):
        _need(type(self.attributes) is int and self.attributes >= 0
              and self.attributes & _DIRECTORY and not self.attributes & _REFUSED_ATTRIBUTES)
        _need(type(self.volume_serial) is int and 0 <= self.volume_serial < 2**32
              and type(self.file_index) is int and 0 < self.file_index < 2**64)
        return self.volume_serial, self.file_index


class NativeDirectoryAPI:
    """Explicit Win32 boundary; injectable methods are used only by contract tests."""
    def __init__(self):
        _need(os.name == 'nt', _UNSUPPORTED)
        import ctypes
        from ctypes import wintypes

        class FileTime(ctypes.Structure):
            _fields_ = [('low', wintypes.DWORD), ('high', wintypes.DWORD)]

        class HandleInformation(ctypes.Structure):
            _fields_ = [('attributes', wintypes.DWORD), ('created', FileTime),
                ('accessed', FileTime), ('written', FileTime), ('volume', wintypes.DWORD),
                ('size_high', wintypes.DWORD), ('size_low', wintypes.DWORD),
                ('links', wintypes.DWORD), ('index_high', wintypes.DWORD), ('index_low', wintypes.DWORD)]

        self._ctypes, self._info_type = ctypes, HandleInformation
        self._kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self._kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        self._kernel.CreateFileW.restype = wintypes.HANDLE
        self._kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.POINTER(HandleInformation)]
        self._kernel.GetFileInformationByHandle.restype = wintypes.BOOL
        self._kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
            wintypes.DWORD, wintypes.DWORD]
        self._kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
        self._kernel.CreateDirectoryW.argtypes = [wintypes.LPCWSTR, wintypes.LPVOID]
        self._kernel.CreateDirectoryW.restype = wintypes.BOOL
        self._kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel.CloseHandle.restype = wintypes.BOOL

    def open_directory(self, path):
        # FILE_READ_ATTRIBUTES; SHARE_READ only; OPEN_EXISTING; no reparse following.
        handle = self._kernel.CreateFileW(path, 0x80, 0x1, None, 3, 0x02000000 | 0x00200000, None)
        _need(handle is not None and handle != 0 and handle != self._ctypes.c_void_p(-1).value)
        return handle

    def information(self, handle):
        info = self._info_type()
        _need(bool(self._kernel.GetFileInformationByHandle(handle, self._ctypes.byref(info))))
        return DirectoryInformation(attributes=int(info.attributes), volume_serial=int(info.volume),
            file_index=(int(info.index_high) << 32) | int(info.index_low))

    def final_path(self, handle):
        buffer = self._ctypes.create_unicode_buffer(_MAX_CHARS + 2)
        size = self._kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        _need(0 < size < len(buffer))
        return buffer.value

    def create_directory(self, path):
        # Only one fixed child under an already held parent; never recursive mkdir.
        if not self._kernel.CreateDirectoryW(path, None):
            _need(self._ctypes.get_last_error() == 183)  # ERROR_ALREADY_EXISTS; the open below verifies type.

    def close(self, handle):
        _need(bool(self._kernel.CloseHandle(handle)))


class WindowsDirectoryPin:
    """A live context's checked path; it does not authorize a leaf or owner event."""
    def __init__(self, api, rows, path):
        self._api, self._rows, self._closed = api, tuple(rows), False
        self.path = path
        self.root_handle = rows[-1][1]
        self.identity = rows[-1][2]

    def check(self):
        _need(not self._closed)
        for path, handle, identity in self._rows:
            info = self._api.information(handle)
            _need(type(info) is DirectoryInformation and info.identity == identity)
            _need(ntpath.normcase(_final_path(self._api.final_path(handle))) == ntpath.normcase(path))


@contextmanager
def pinned_research_anchor_directory(home: Path, *, api=None):
    """Pin existing compliance home, then create/pin approved/research-attestations.

    Yields a pin with Path ``path``, ``identity`` and ``check()``. Keep the context
    open through the caller's exclusive leaf creation, readback and flush. A
    supplied fake API plus PureWindowsPath permits hermetic tests on POSIX; the
    normal POSIX call refuses before I/O. Native Windows behavior remains a
    separate validation obligation. No key, log, anchor file or home is selected
    implicitly, and an absent compliance home is never created here.
    """
    _need(os.name == 'nt' or api is not None, _UNSUPPORTED)
    _need(isinstance(home, Path) or (api is not None and type(home) is PureWindowsPath))
    path = _lexical_path(str(home))
    try:
        native = NativeDirectoryAPI() if api is None else api
    except RevocationPathError:
        raise
    except (OSError, AttributeError, TypeError, RuntimeError):
        raise RevocationPathError(_UNSUPPORTED) from None
    rows, handles, pin = [], [], None
    drive, root, tail = ntpath.splitroot(path)
    prefixes = [drive + root]
    for part in tail.split('\\') if tail else ():
        prefixes.append(ntpath.join(prefixes[-1], part))

    def retain(prefix):
        handle = native.open_directory(prefix)
        handles.append(handle)
        info = native.information(handle)
        _need(type(info) is DirectoryInformation)
        identity = info.identity
        _need(ntpath.normcase(_final_path(native.final_path(handle))) == ntpath.normcase(prefix))
        rows.append((prefix, handle, identity))

    try:
        for prefix in prefixes:
            retain(prefix)
        for child in ('approved', 'research-attestations'):
            # Recheck every retained ancestor before and after creating this one child.
            WindowsDirectoryPin(native, rows, home).check()
            path = ntpath.join(path, child)
            native.create_directory(path)
            WindowsDirectoryPin(native, rows, home).check()
            retain(path)
        pin = WindowsDirectoryPin(native, rows, home / 'approved' / 'research-attestations')
        pin.check()
        try:
            yield pin
        finally:
            pin.check()
    except RevocationPathError:
        raise
    except (OSError, ValueError, TypeError, AttributeError, RuntimeError, OverflowError):
        raise RevocationPathError(_REFUSED) from None
    finally:
        if pin is not None:
            pin._closed = True
        failed = False
        for handle in reversed(handles):
            try:
                native.close(handle)
            except Exception:
                failed = True
        if failed:
            raise RevocationPathError(_REFUSED) from None
