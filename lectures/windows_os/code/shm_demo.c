// shm_demo.c - two processes share one page through a named section,
// guard it with a named mutex, and signal each other with named events.
// Build (Visual Studio Developer Prompt):  cl /W4 shm_demo.c
// Build (MinGW):                          x86_64-w64-mingw32-gcc -Wall -o shm_demo.exe shm_demo.c
// Run:  start "reader" shm_demo.exe reader      then      shm_demo.exe writer
#include <windows.h>
#include <stdio.h>
#include <string.h>

#define SECTION_NAME L"Local\\ShmDemoSection"   // the name IS the agreement
#define MUTEX_NAME   L"Local\\ShmDemoLock"
#define READY_NAME   L"Local\\ShmDemoReady"     // writer -> reader: "a message is waiting"
#define ACK_NAME     L"Local\\ShmDemoAck"       // reader -> writer: "I consumed it"

typedef struct {
    LONG sequence;        // which message this is (0 = none yet)
    LONG length;          // bytes used in text[]
    char text[248];       // payload: plain data only, never pointers
} SHARED_BLOCK;           // 256 bytes; the section is one 4 KB page

static void die(const char *what) {
    printf("%s failed, GetLastError=%lu\n", what, GetLastError());
    ExitProcess(1);
}

int main(int argc, char **argv) {
    int isWriter = (argc > 1 && strcmp(argv[1], "writer") == 0);

    // 1. Create the section, or open it if the other process created it first.
    //    INVALID_HANDLE_VALUE = back it with the page file, not a disk file.
    HANDLE section = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE,
                                        0, 4096, SECTION_NAME);
    if (!section) die("CreateFileMappingW");
    BOOL alreadyExisted = (GetLastError() == ERROR_ALREADY_EXISTS);

    // 2. Map a view: this is where the kernel edits THIS process's page tables.
    SHARED_BLOCK *block = (SHARED_BLOCK *)MapViewOfFile(section, FILE_MAP_ALL_ACCESS, 0, 0, 4096);
    if (!block) die("MapViewOfFile");

    // 3. Named kernel objects for synchronization. Same naming mechanism as the section.
    HANDLE lock  = CreateMutexW(NULL, FALSE, MUTEX_NAME);          // not owned at creation
    HANDLE ready = CreateEventW(NULL, FALSE, FALSE, READY_NAME);   // auto-reset, starts unsignaled
    HANDLE ack   = CreateEventW(NULL, FALSE, FALSE, ACK_NAME);
    if (!lock || !ready || !ack) die("CreateMutexW/CreateEventW");

    printf("[%s pid %lu] section %s, view mapped at virtual address %p\n",
           isWriter ? "writer" : "reader", GetCurrentProcessId(),
           alreadyExisted ? "opened" : "created", (void *)block);

    for (int i = 1; i <= 3; i++) {
        if (isWriter) {
            WaitForSingleObject(lock, INFINITE);            // enter critical section
            block->sequence = i;
            block->length = sprintf(block->text, "message %d from pid %lu", i, GetCurrentProcessId());
            ReleaseMutex(lock);                             // leave critical section
            SetEvent(ready);                                // wake the reader
            WaitForSingleObject(ack, INFINITE);             // sleep until it's consumed
        } else {
            WaitForSingleObject(ready, INFINITE);           // sleep (no CPU) until signaled
            WaitForSingleObject(lock, INFINITE);
            printf("[reader] seq=%ld text=\"%.*s\"\n", block->sequence, (int)block->length, block->text);
            ReleaseMutex(lock);
            SetEvent(ack);
        }
    }

    // 4. Clean up. The section is destroyed when the LAST handle and view are gone.
    UnmapViewOfFile(block);
    CloseHandle(section); CloseHandle(lock); CloseHandle(ready); CloseHandle(ack);
    return 0;
}
