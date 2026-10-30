// tgclient.c - Phase 5 client.  Usage:
//   tgclient            -> INCREMENT three times (same as before)
//   tgclient get        -> print the current counter without changing it
//   tgclient crash      -> LAB 5.3: ask the driver to crash the machine (bugcheck!)
//   tgclient paged      -> LAB 5.4: ask the driver to read paged pool at DISPATCH_LEVEL
#include <windows.h>
#include <winioctl.h>
#include <stdio.h>
#include <string.h>
#include "tgcounter_ioctl.h"

static int SendIoctl(HANDLE h, DWORD code, const char *label)
{
    LONG value = 0; DWORD bytes = 0;
    if (!DeviceIoControl(h, code, NULL, 0, &value, sizeof(value), &bytes, NULL)) {
        printf("%s: DeviceIoControl failed, GetLastError=%lu\n", label, GetLastError());
        return 1;
    }
    printf("%s -> %ld (%lu bytes returned)\n", label, value, bytes);
    return 0;
}

int main(int argc, char **argv)
{
    const char *mode = (argc > 1) ? argv[1] : "increment";

    HANDLE h = CreateFileW(TGCOUNTER_USER_PATH, GENERIC_READ | GENERIC_WRITE, 0, NULL,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) {
        printf("CreateFile failed, GetLastError=%lu (2 = no such name: is the driver loaded?)\n",
               GetLastError());
        return 1;
    }

    int rc = 0;
    if (strcmp(mode, "get") == 0) {
        rc = SendIoctl(h, IOCTL_TGCOUNTER_GET, "GET");
    } else if (strcmp(mode, "crash") == 0) {
        printf("Sending IOCTL_TGCOUNTER_CRASH (0x%08lX). The VM should blue-screen now.\n",
               (unsigned long)IOCTL_TGCOUNTER_CRASH);
        fflush(stdout);
        rc = SendIoctl(h, IOCTL_TGCOUNTER_CRASH, "CRASH");
    } else if (strcmp(mode, "paged") == 0) {
        printf("Sending IOCTL_TGCOUNTER_PAGED_AT_DISPATCH (0x%08lX).\n",
               (unsigned long)IOCTL_TGCOUNTER_PAGED_AT_DISPATCH);
        fflush(stdout);
        rc = SendIoctl(h, IOCTL_TGCOUNTER_PAGED_AT_DISPATCH, "PAGED");
    } else {
        for (int i = 0; i < 3 && rc == 0; i++)
            rc = SendIoctl(h, IOCTL_TGCOUNTER_INCREMENT, "INCREMENT");
    }

    CloseHandle(h);
    return rc;
}
