/*
 * 016_ecoqos_and_timers.c - lecture 016.
 * A background worker that is kind to the battery:
 *   1. tags its own process as EcoQoS (efficient cores / efficient frequency),
 *   2. waits on a timer that allows Windows to delay it (coalescing) instead of a tight Sleep loop,
 *   3. restores the default (let Windows decide) before exiting.
 * Build (Developer Command Prompt):  cl /W4 016_ecoqos_and_timers.c
 * Compile-checked here with MinGW:   x86_64-w64-mingw32-gcc -Wall -Wextra -c 016_ecoqos_and_timers.c
 */
#include <windows.h>
#include <stdio.h>

static BOOL SetEcoQoS(BOOL on)
{
    PROCESS_POWER_THROTTLING_STATE s;
    ZeroMemory(&s, sizeof s);
    s.Version     = PROCESS_POWER_THROTTLING_CURRENT_VERSION;
    s.ControlMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED;     /* "I am deciding this feature" */
    s.StateMask   = on ? PROCESS_POWER_THROTTLING_EXECUTION_SPEED /* set   -> EcoQoS             */
                       : 0;                                       /* clear -> HighQoS             */
    return SetProcessInformation(GetCurrentProcess(), ProcessPowerThrottling, &s, sizeof s);
}

static BOOL LetWindowsDecide(void)
{
    PROCESS_POWER_THROTTLING_STATE s;
    ZeroMemory(&s, sizeof s);
    s.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION;         /* ControlMask 0: no opinion    */
    return SetProcessInformation(GetCurrentProcess(), ProcessPowerThrottling, &s, sizeof s);
}

static void DoOneBatchOfBackgroundWork(int i)
{
    printf("batch %d at tick %llu\n", i, (unsigned long long)GetTickCount64());
}

int main(void)
{
    if (!SetEcoQoS(TRUE))
        printf("SetProcessInformation failed: %lu\n", GetLastError());

    HANDLE timer = CreateWaitableTimerExW(NULL, NULL, 0, TIMER_ALL_ACCESS);
    if (!timer) { printf("CreateWaitableTimerEx failed: %lu\n", GetLastError()); return 1; }

    LARGE_INTEGER due;
    due.QuadPart = -10LL * 1000 * 1000 * 5;   /* first expiry: 5 s from now (negative = relative, 100 ns units) */
    /* Period 5000 ms, tolerable delay 1000 ms: Windows may fire up to 1 s late so it can
       batch this wake-up with others and keep the CPU idle longer. */
    if (!SetWaitableTimerEx(timer, &due, 5000, NULL, NULL, NULL, 1000)) {
        printf("SetWaitableTimerEx failed: %lu\n", GetLastError());
        return 1;
    }

    for (int i = 0; i < 3; i++) {
        WaitForSingleObject(timer, INFINITE);  /* the thread is blocked, not spinning: zero CPU */
        DoOneBatchOfBackgroundWork(i);
    }

    CloseHandle(timer);
    LetWindowsDecide();
    return 0;
}
