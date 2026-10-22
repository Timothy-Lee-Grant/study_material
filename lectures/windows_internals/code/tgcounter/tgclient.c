// tgclient.c - user-mode program that talks to the TgCounter driver.
#include <windows.h>
#include <winioctl.h>      // CTL_CODE, METHOD_BUFFERED, FILE_ANY_ACCESS ...
#include <stdio.h>
#include "tgcounter_ioctl.h"

int main(void)
{
    printf("IOCTL_TGCOUNTER_INCREMENT = 0x%08lX\n", (unsigned long)IOCTL_TGCOUNTER_INCREMENT);
    printf("IOCTL_TGCOUNTER_GET       = 0x%08lX\n", (unsigned long)IOCTL_TGCOUNTER_GET);

    // 1. Open the device by its symbolic link. This becomes IRP_MJ_CREATE in the driver.
    HANDLE h = CreateFileW(TGCOUNTER_USER_PATH, GENERIC_READ | GENERIC_WRITE, 0, NULL,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) {
        printf("CreateFile failed, GetLastError=%lu (2 = no such name: is the driver loaded?)\n",
               GetLastError());
        return 1;
    }

    // 2. Send requests. Each DeviceIoControl becomes one IRP_MJ_DEVICE_CONTROL.
    for (int i = 0; i < 3; i++) {
        LONG value = 0; DWORD bytes = 0;
        if (!DeviceIoControl(h, IOCTL_TGCOUNTER_INCREMENT, NULL, 0,
                             &value, sizeof(value), &bytes, NULL)) {
            printf("DeviceIoControl failed, GetLastError=%lu\n", GetLastError());
            break;
        }
        printf("INCREMENT -> %ld (%lu bytes returned)\n", value, bytes);
    }

    // 3. Close. This becomes IRP_MJ_CLOSE (after the last handle to the file object closes).
    CloseHandle(h);
    return 0;
}
