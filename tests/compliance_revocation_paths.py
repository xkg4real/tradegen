"""Hermetic Win32 pin contracts, not actual Windows filesystem validation.

No owner home, key, log, anchor bytes, network or real Win32 call is used. The
native Windows sharing/reparse/creation/power-loss behavior remains NOT_RUN.
"""
import ctypes
import ntpath
import os
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace

from core.compliance import revocation_paths as R

HOME = PureWindowsPath('C:/synthetic-owner/compliance')
EXISTING = ('C:\\', 'C:\\synthetic-owner', 'C:\\synthetic-owner\\compliance')
CHILDREN = ('C:\\synthetic-owner\\compliance\\approved',
            'C:\\synthetic-owner\\compliance\\approved\\research-attestations')


def refused(call, code=R._REFUSED):
    try:
        call()
    except R.RevocationPathError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError('unsafe or unsupported directory pin accepted')


class FakeAPI:
    """Records real call ordering/active handles, not a permissive True verifier."""
    def __init__(self, existing=EXISTING):
        self.existing = set(existing)
        self.opened, self.closed, self.created, self.operations = [], [], [], []
        self.active, self.attributes, self.indices, self.final = {}, {}, {}, {}
        self.fail_open = self.fail_create = self.fail_close = None

    def open_directory(self, path):
        self.operations.append(('open', path))
        if path == self.fail_open or path not in self.existing:
            raise OSError('synthetic missing/refused directory; never exposed')
        self.opened.append(path)
        handle = len(self.opened)
        self.active[handle] = path
        return handle

    def information(self, handle):
        assert handle in self.active
        return R.DirectoryInformation(attributes=self.attributes.get(handle, 16), volume_serial=7,
                                      file_index=self.indices.get(handle, handle))

    def final_path(self, handle):
        assert handle in self.active
        return self.final.get(handle, '\\\\?\\' + self.active[handle])

    def create_directory(self, path):
        # Creating a descendant without retaining its actual parent fails this test API.
        assert ntpath.dirname(path) in self.active.values()
        assert all(parent in self.active.values() for parent in EXISTING)
        self.operations.append(('create', path))
        if path == self.fail_create:
            raise OSError('synthetic directory creation failed')
        self.created.append(path)
        self.existing.add(path)

    def close(self, handle):
        self.closed.append(handle)
        self.active.pop(handle)
        if handle == self.fail_close:
            raise OSError('synthetic close failure')


def entered(home, api):
    with R.pinned_research_anchor_directory(home, api=api) as pin:
        pin.check()


def test_pins_all_existing_ancestors_before_sequential_fixed_child_creation():
    api = FakeAPI()
    context = R.pinned_research_anchor_directory(HOME, api=api)
    assert not api.operations
    with context as pin:
        assert pin.path == HOME/'approved'/'research-attestations'
        assert pin.identity == (7, 5) and pin.root_handle == 5
        assert set(api.active) == set(range(1, 6))
        pin.check()
    assert api.operations == ([('open', path) for path in EXISTING]
        + [('create', CHILDREN[0]), ('open', CHILDREN[0]), ('create', CHILDREN[1]), ('open', CHILDREN[1])])
    assert api.closed == [5, 4, 3, 2, 1] and not api.active
    refused(pin.check)


def test_existing_children_are_reopened_and_validated_without_removing_them():
    api = FakeAPI(EXISTING + CHILDREN)
    entered(HOME, api)
    assert api.created == list(CHILDREN) and api.existing == set(EXISTING + CHILDREN)
    assert api.closed == [5, 4, 3, 2, 1]


def test_absent_home_is_not_created_and_prior_handles_close():
    api = FakeAPI(EXISTING[:2])
    refused(lambda:entered(HOME, api))
    assert not api.created and api.closed == [2, 1] and not api.active


def test_create_or_child_open_failure_closes_every_acquired_handle():
    for stage in ('create-first', 'create-second', 'open-first', 'open-second'):
        api = FakeAPI()
        target = CHILDREN[0 if stage.endswith('first') else 1]
        if stage.startswith('create'): api.fail_create = target
        else: api.fail_open = target
        refused(lambda:entered(HOME, api))
        assert api.closed == list(reversed(range(1, len(api.opened)+1))) and not api.active
        assert not any('compliance' == ntpath.basename(path) for path in api.created)


def test_reparse_placeholder_non_directory_or_unavailable_identity_refuses_before_creation():
    for attribute in (0, 0x10 | 0x400, 0x10 | 0x1000, 0x10 | 0x40000, 0x10 | 0x400000):
        api = FakeAPI(); api.attributes[2] = attribute
        refused(lambda:entered(HOME, api))
        assert api.closed == [2, 1] and not api.created
    api = FakeAPI(); api.indices[2] = 0
    refused(lambda:entered(HOME, api))
    assert api.closed == [2, 1] and not api.created


def test_created_child_cannot_be_substituted_with_reparse_or_redirected_path():
    for mode in ('reparse', 'path'):
        api = FakeAPI()
        if mode == 'reparse': api.attributes[4] = 0x10 | 0x400
        else: api.final[4] = '\\\\?\\C:\\different-location'
        refused(lambda:entered(HOME, api))
        assert api.created == [CHILDREN[0]] and api.closed == [4, 3, 2, 1]


def test_pinned_identity_reparse_and_final_path_changes_are_checked_until_exit():
    for mode in ('identity', 'reparse', 'path'):
        api = FakeAPI()
        def change():
            with R.pinned_research_anchor_directory(HOME, api=api):
                if mode == 'identity': api.indices[2] = 99
                elif mode == 'reparse': api.attributes[2] = 0x10 | 0x400
                else: api.final[2] = '\\\\?\\C:\\replacement'
        refused(change)
        assert api.closed == [5, 4, 3, 2, 1] and not api.active


def test_alias_finalpaths_unc_devices_and_reserved_names_cannot_be_accepted():
    for changed in ('\\\\?\\C:\\OTHER~1', '\\\\?\\D:\\synthetic-owner',
                    '\\\\?\\UNC\\server\\share', '\\\\?\\Volume{fake}\\'):
        api = FakeAPI(); api.final[2] = changed
        refused(lambda:entered(HOME, api))
        assert not api.created and not api.active
    for path in (PureWindowsPath('//server/share/owner'), PureWindowsPath('C:relative'),
                 PureWindowsPath('C:/owner/../home'), PureWindowsPath('C:/con'),
                 PureWindowsPath('C:/owner:stream'), PureWindowsPath('//?/C:/owner')):
        api = FakeAPI()
        refused(lambda:entered(path, api))
        assert not api.operations


def test_one_close_failure_does_not_leak_the_remaining_ancestors():
    api = FakeAPI(); api.fail_close = 4
    refused(lambda:entered(HOME, api))
    assert api.closed == [5, 4, 3, 2, 1] and not api.active


def test_body_exception_releases_all_handles_without_deleting_created_directories():
    api = FakeAPI()
    try:
        with R.pinned_research_anchor_directory(HOME, api=api):
            raise LookupError('synthetic caller interruption')
    except LookupError:
        pass
    else:
        raise AssertionError('caller interruption swallowed')
    assert api.closed == [5, 4, 3, 2, 1] and api.existing == set(EXISTING + CHILDREN)


def test_native_open_uses_attributes_read_sharing_only_and_no_reparse_follow():
    calls = []
    class Kernel:
        def CreateFileW(self, *args): calls.append(args); return 7
    native = R.NativeDirectoryAPI.__new__(R.NativeDirectoryAPI)
    native._kernel, native._ctypes = Kernel(), ctypes
    assert native.open_directory('C:\\synthetic') == 7
    assert calls == [('C:\\synthetic', 0x80, 0x1, None, 3, 0x02000000 | 0x00200000, None)]
    for invalid in (None, 0, ctypes.c_void_p(-1).value):
        native._kernel = SimpleNamespace(CreateFileW=lambda *_, result=invalid: result)
        refused(lambda:native.open_directory('C:\\synthetic'))


def test_native_creation_accepts_only_success_or_already_exists_then_requires_open_validation():
    calls = []
    native = R.NativeDirectoryAPI.__new__(R.NativeDirectoryAPI)
    native._kernel = SimpleNamespace(CreateDirectoryW=lambda *args: calls.append(args) or False)
    native._ctypes = SimpleNamespace(get_last_error=lambda:183)
    native.create_directory('C:\\synthetic\\approved')
    assert calls == [('C:\\synthetic\\approved', None)]
    for code in (2, 3, 5, 32):
        native._ctypes = SimpleNamespace(get_last_error=lambda code=code:code)
        refused(lambda:native.create_directory('C:\\synthetic\\approved'))


def test_default_posix_call_refuses_without_creating_or_opening_any_owner_path():
    if os.name == 'nt':
        from tests.notrun import NotRun
        raise NotRun('POSIX refusal is not a native Windows operation test')
    def call():
        with R.pinned_research_anchor_directory(Path('/synthetic-owner-does-not-exist')):
            raise AssertionError('POSIX native fallback entered')
    refused(call, R._UNSUPPORTED)


def test_information_rejects_boolean_negative_or_unavailable_native_identity():
    for values in ((True,7,1), (16,True,1), (16,-1,1), (16,2**32,1), (16,7,True),
                   (16,7,0), (16,7,-1), (16,7,2**64)):
        refused(lambda:R.DirectoryInformation(attributes=values[0], volume_serial=values[1],
                                              file_index=values[2]).identity)
