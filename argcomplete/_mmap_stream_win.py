#!/usr/bin/env python3

import sys
from ctypes import windll, cdll,\
    c_char_p, c_wchar, c_size_t, c_ulonglong, c_wchar_p, c_void_p,\
    sizeof,\
    WinError
from ctypes.wintypes import BOOL, DWORD, HANDLE, LPCWSTR, LPCVOID, LPVOID

class MappedMemoryStream:
    def __init__(self, mmf_name):
        self._name = mmf_name

    def write(self, data):
        print("Python {:s} on {:s}".format(sys.version, sys.platform))

        # Constants
        FILE_MAP_ALL_ACCESS = 0x000F001F
        SHMEMSIZE = 0x100

        # Function definitions
        kernel32_dll = windll.kernel32
        msvcrt_dll = cdll.msvcrt

        open_file_mapping_func = kernel32_dll.OpenFileMappingW
        open_file_mapping_func.argtypes = (DWORD, BOOL, LPCWSTR)
        open_file_mapping_func.restype = HANDLE

        map_view_of_file_func = kernel32_dll.MapViewOfFile
        map_view_of_file_func.argtypes = (HANDLE, DWORD, DWORD, DWORD, c_ulonglong)
        map_view_of_file_func.restype = LPVOID

        memcpy_func = msvcrt_dll.memcpy
        memcpy_func.argtypes = (c_void_p, c_void_p, c_size_t)
        memcpy_func.restype = LPVOID

        unmap_view_of_file_func = kernel32_dll.UnmapViewOfFile
        unmap_view_of_file_func.argtypes = (LPCVOID,)
        unmap_view_of_file_func.restype = BOOL

        close_handle_func = kernel32_dll.CloseHandle
        close_handle_func.argtypes = (HANDLE,)
        close_handle_func.restype = BOOL

        get_last_error_func = kernel32_dll.GetLastError

        # Connect to the memory mapped file
        file_mapping_name_ptr = c_wchar_p(self._name)
        mapping_handle = open_file_mapping_func(FILE_MAP_ALL_ACCESS, False, file_mapping_name_ptr)

        print("Mapping object handle: 0x{:016X}".format(mapping_handle))
        if not mapping_handle:
            print("Could not open file mapping object: {:d}".format(get_last_error_func()))
            raise WinError()

        mapped_view_ptr = map_view_of_file_func(mapping_handle, FILE_MAP_ALL_ACCESS, 0, 0, SHMEMSIZE)
        err = get_last_error_func()
        print(err)

        print("Mapped view addr: 0x{:016X}".format(mapped_view_ptr))
        if not mapped_view_ptr:
            print("Could not map view of file: {:d}".format(get_last_error_func()))
            close_handle_func(mapping_handle)
            raise WinError()

        # Write data into the file
        data_ptr = c_char_p(data)
        byte_len = len(data)
    
        print("Message length: {:d} chars ({:d} bytes)".format(len(data), byte_len))

        memcpy_func(mapped_view_ptr, data_ptr, byte_len)

        # Detach
        unmap_view_of_file_func(mapped_view_ptr)
        close_handle_func(mapping_handle)

    def flush(self):
        # Just for the compatibility
        pass


# Just an example of usage    
if __name__ == "__main__":
    import os
    import locale

    msg = "Here is a new message."

    # output_stream = os.fdopen(2, "wb")
    output_stream = MappedMemoryStream("test_mmf")
    output_stream.write(msg.encode(locale.getpreferredencoding()))
    output_stream.flush()
