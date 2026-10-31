# Lecture 017: The Windows App Platform (WinUI 3 and the Windows App SDK) and Open-Source Projects to Learn From

> **For:** Timothy · **Date:** 2026-10-31
> **Prerequisites:** 008 (processes and threads), 009 (drivers and the request path), 015 (traces, WPA, Profile Explorer). Helpful: 014 §8 (reader thread + UI thread).
> **Why this lecture:** your lectures so far go from the hardware up to the driver and the app's `ReadFile`. This one covers the layer above: how a modern Windows desktop app is built (WinUI 3 on the Windows App SDK), how it relates to Win32 and the OS, and where its performance and memory come from. It also covers four Microsoft open-source repositories worth knowing, two from the app platform and two from performance tooling, with concrete projects that connect them to the driver work you've already done.
> **Format notes:** facts about project status are dated, because they change. Code is a sketch unless marked otherwise. No firmware analogies.

---

## Core ideas (the answer key)

1. **A Windows desktop app is a Win32 process** no matter which UI framework it uses. Frameworks (Win32/USER32, WPF, WinForms, WinUI) are libraries the process loads; they draw through the same OS composition engine (DWM).
2. **WinUI 3 is Microsoft's current native UI framework for desktop apps.** It's a XAML-based UI library that ships **with the app** (as part of the Windows App SDK), not inside Windows. That decoupling lets it update independently and run on Windows 10 version 1809 and later.
3. **The Windows App SDK (WASDK, formerly Project Reunion)** is the set of libraries around WinUI 3: windowing (`AppWindow`), app lifecycle and activation, resources (MRT Core), text (DWriteCore), notifications, and deployment. Microsoft now treats WinUI and WASDK as one product, called WinUI.
4. **Every WinUI window has one UI thread** with a `DispatcherQueue`. Code that touches UI elements must run there; long work runs elsewhere and posts results back with `DispatcherQueue.TryEnqueue`.
5. **Packaged vs unpackaged, framework-dependent vs self-contained:** an app can be installed as MSIX (packaged, with identity) or as plain files (unpackaged), and can use a shared WASDK runtime installed on the machine (framework-dependent) or carry its own copy (self-contained).
6. **WinUI's code is on GitHub** (`microsoft/microsoft-ui-xaml`, `microsoft/WindowsAppSDK`, MIT license). As of late August 2026, mainline WinUI development happens on GitHub, but only Microsoft employees change the code; community code contributions are planned next. Issues and discussions are open now.
7. **Performance tooling is also open:** `microsoft/profile-explorer` (CPU profile analysis down to assembly, x64 and ARM64) and `microsoft/microsoft-performance-toolkit-sdk` (the runtime under WPA, used to write WPA plugins). Both MIT; contributions under Microsoft's CLA.
8. **Your best entry point combines what you have:** add ETW events (TraceLogging) to your TgCounter driver, view them in WPA, write a Performance Toolkit SDK plugin that turns them into a latency table, and build a small WinUI app that talks to the driver with a reader thread. That one project touches drivers, ETW, WPA, the SDK and WinUI.

---

## Table of Contents

- [1. How a Windows desktop app is put together](#1-how-a-windows-desktop-app-is-put-together)
- [2. WinUI 3 and the Windows App SDK](#2-winui-3-and-the-windows-app-sdk)
- [3. The UI thread and the dispatcher queue](#3-the-ui-thread-and-the-dispatcher-queue)
- [4. Deployment: packaged, unpackaged, framework-dependent, self-contained](#4-deployment-packaged-unpackaged-framework-dependent-self-contained)
- [5. Why WinUI performance and memory matter](#5-why-winui-performance-and-memory-matter)
- [6. The four repositories](#6-the-four-repositories)
- [7. A connected project: TgCounter end to end](#7-a-connected-project-tgcounter-end-to-end)
- [8. How to contribute to a large Microsoft repo](#8-how-to-contribute-to-a-large-microsoft-repo)
- [Common mistakes](#common-mistakes)
- [Self-check questions](#self-check-questions)
- [Sources](#sources)

---

## 1. How a Windows desktop app is put together

From the bottom up, using what you already know:

```
 your app code (C#, C++)
      │
 UI framework (WinUI 3 / WPF / WinForms / raw Win32)        ← a library in your process
      │
 Win32 APIs: USER32 (windows, messages), GDI/Direct2D/DirectWrite, Direct3D, composition
      │
 kernel32 / ntdll ──► system calls ──► kernel (I/O manager, drivers: lectures 005–009)
      │
 DWM (Desktop Window Manager): composes every app's windows into the final screen image
```

- **A window** is a kernel-managed object (an `HWND`) owned by a thread. Input arrives as **messages** in that thread's message queue; the thread's message loop takes them out and dispatches them. That's why a busy UI thread freezes its windows: nobody is taking the messages out.
- **Drawing** today goes through Direct3D/Direct2D and the composition engine. Each app renders into surfaces, and DWM combines them.
- **WinRT** (Windows Runtime) is a way of exposing OS and library APIs as objects with metadata, callable naturally from C#, C++ (C++/WinRT), and other languages. WinUI 3 and WASDK APIs are WinRT APIs, which is why they look the same from C# and C++.

Every framework sits on this stack. What differs is how much it does for you and how it draws.

---

## 2. WinUI 3 and the Windows App SDK

**A short history, because the names are confusing:**

| Name | What it was |
|---|---|
| UWP XAML (`Windows.UI.Xaml`) | the XAML UI framework built into Windows 8/10, for UWP (sandboxed Store) apps; updated only with Windows |
| WinUI 2 | a library of newer controls for UWP XAML apps, shipped as a NuGet package |
| **WinUI 3** (`Microsoft.UI.Xaml`) | the whole XAML framework lifted **out of Windows** into a library shipped with the app, for desktop (Win32) apps |
| Project Reunion → **Windows App SDK** | the larger set of app libraries that WinUI 3 ships in |

**What the Windows App SDK contains** (from its repository and documentation):
- **WinUI 3**: controls, layout, data binding, styles, XAML markup.
- **Windowing**: `AppWindow` and related APIs for managing top-level windows.
- **App lifecycle**: activation (launched by file type, protocol, notification), single-instancing, restart.
- **MRT Core**: resource loading (localized strings, scaled images).
- **DWriteCore**: the DirectWrite text engine as a library.
- **Notifications**: app and push notifications.
- **Deployment**: APIs to check and install the runtime the app needs.

**Why "decoupled from the OS" matters.** UWP XAML could only improve when Windows itself shipped a new version, and apps had to wait for users to upgrade Windows. WinUI 3 ships with the app, so a fix or a new control reaches users as soon as the app updates, and the same app runs back to Windows 10 version 1809.

Microsoft now describes WinUI 3 and the Windows App SDK together as one product, **WinUI**.

---

## 3. The UI thread and the dispatcher queue

Each WinUI window belongs to a **UI thread**, and UI objects can only be touched from that thread. The thread runs a loop that processes input, layout and rendering. WinUI exposes the thread's work queue as a **`DispatcherQueue`**.

Lecture 014's reader-thread pattern, in WinUI (C#, sketch):

```csharp
// In the window: start a background reader; never block the UI thread.
private readonly DispatcherQueue _ui = DispatcherQueue.GetForCurrentThread();
private CancellationTokenSource _cts = new();

private void StartReading(SafeFileHandle device)
{
    _ = Task.Run(async () =>
    {
        using var stream = new FileStream(device, FileAccess.Read, bufferSize: 4096, isAsync: true);
        var buffer = new byte[4096];
        var parser = new PacketParser();                 // leetcode/019, ported to C#
        while (!_cts.IsCancellationRequested)
        {
            int n = await stream.ReadAsync(buffer, _cts.Token);   // completes when the driver completes the read
            if (n == 0) break;
            parser.Feed(buffer.AsSpan(0, n));
            var packets = parser.GetAllPackets();
            if (packets.Count > 0)
                _ui.TryEnqueue(() => ShowPackets(packets));      // runs on the UI thread
        }
    });
}
```

- `await stream.ReadAsync(...)` doesn't hold a thread while the driver's read is pending (overlapped I/O underneath).
- `TryEnqueue` posts a delegate to the UI thread's queue; `ShowPackets` runs there and can touch controls.
- Cancelling `_cts` cancels the pending read, which cancels the driver's parked request (lecture 014 §5).

---

## 4. Deployment: packaged, unpackaged, framework-dependent, self-contained

Two independent choices:

| | Meaning | Trade-off |
|---|---|---|
| **Packaged** (MSIX) | installed as a package with **package identity** | clean install/uninstall, identity-based features (some notifications, background tasks); needs signing |
| **Unpackaged** | plain files (xcopy or a classic installer) | familiar, but no package identity |
| **Framework-dependent** | uses the WASDK runtime installed on the machine as a shared framework package | smaller app; the runtime must be present (the app or installer can install it) |
| **Self-contained** | carries its own copy of the WASDK runtime | larger app; no dependency to install |

Why a platform engineer should care: deployment decides **which binaries load** in the process (shared runtime vs the app's copy), which matters when you're reading a crash dump or a trace and need to know which version of a DLL was running.

---

## 5. Why WinUI performance and memory matter

WinUI is no longer only for third-party apps. In its July 31, 2026 update on Windows quality, the Windows team said WinUI 3's fundamentals have been strengthened and extended into more of the Windows shell (Widgets, the new Run experience, and more dialogs in Insider builds), that WinUI 3 is being tuned so apps built on it **use less memory**, and that these investments brought "substantial improvements in memory efficiency and latency". The same update describes work on app launch, responsiveness, and a more efficient memory allocator across Windows.

So the framework's startup time, memory per window, and UI-thread responsiveness now show up directly in how Windows itself feels. The tools for measuring them are the ones from lecture 015 (CPU sampling, waits on the UI thread) plus memory tools (WPA's memory tables; heap and VirtualAlloc tracing).

Typical WinUI performance questions, and how you'd approach them:
- **Slow first window:** a trace from process start to first frame; what's on the UI thread (XAML parsing, layout, loading assemblies, disk I/O)?
- **Stutter while scrolling:** UI thread busy for longer than a frame (16.7 ms at 60 Hz); find the work with CPU Usage (Sampled) filtered to the UI thread, and the waits with Precise.
- **Memory per window:** private bytes over time; which allocations (heap tracing) grow with each window opened.

---

## 6. The four repositories

Status as of 2026-10-31 (check each README for current state).

| Repo | What it is | Language / license | Contributions |
|---|---|---|---|
| [`microsoft/microsoft-ui-xaml`](https://github.com/microsoft/microsoft-ui-xaml) | WinUI (the XAML framework) | C++, MIT | Mainline development moved to GitHub (reported Aug 29, 2026); code changes by Microsoft engineers for now; community code contributions planned next. Issues and discussions open. |
| [`microsoft/WindowsAppSDK`](https://github.com/microsoft/WindowsAppSDK) | the SDK libraries around WinUI (formerly Project Reunion) | C++, MIT | Issues, discussions and contributions per its CONTRIBUTING guide |
| [`microsoft/profile-explorer`](https://github.com/microsoft/profile-explorer) | CPU profile (ETW) analysis: hot functions, flame graph, timeline, assembly and source views; x64 and native ARM64 | C# (WPF, .NET 8), MIT | Accepted under Microsoft's CLA |
| [`microsoft/microsoft-performance-toolkit-sdk`](https://github.com/microsoft/microsoft-performance-toolkit-sdk) | the runtime of Windows Performance Analyzer; write plugins that add data sources and tables to WPA | C# (.NET), MIT | Welcomed under the CLA |

**The WinUI open-source plan, briefly.** In August 2025 a Microsoft engineer outlined four phases: mirror code to GitHub more often; let outside developers build it themselves; let outside developers submit pull requests and run tests locally; make GitHub the primary repository. By the end of August 2026, mainline development was on GitHub with engineers opening branches and pull requests there, while direct changes were still limited to Microsoft employees until the workflow is proven.

**What each repo teaches you:**
- **microsoft-ui-xaml:** how a large C++ UI framework is structured (controls, layout, rendering, input), and how its issues are triaged: a stream of real bug reports with repros.
- **WindowsAppSDK:** how OS features are packaged as libraries that ship outside the OS, and the deployment and versioning problems that creates.
- **profile-explorer:** how ETW traces are parsed, how samples map to functions and instructions, and how disassembly works for x64 and ARM64. Directly useful for performance work.
- **performance-toolkit-sdk:** how WPA's data pipeline works (data sources → processing → tables), and how to extend it.

---

## 7. A connected project: TgCounter end to end

One project that uses everything above with the driver you already built and loaded in your VM:

**Step 1: add ETW events to the driver (TraceLogging).** TraceLogging is the simplest way to emit ETW events; it works in kernel mode.

```c
#include <TraceLoggingProvider.h>

TRACELOGGING_DEFINE_PROVIDER(g_TgProvider, "TgCounter",
    /* generate your own GUID; this one is a placeholder pattern */
    (0x12345678, 0x1234, 0x1234, 0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc, 0xde, 0xf0));

/* DriverEntry:  TraceLoggingRegister(g_TgProvider);
   Unload:       TraceLoggingUnregister(g_TgProvider); */

/* In the IOCTL dispatch, around the work: */
TraceLoggingWrite(g_TgProvider, "IoctlStart",
    TraceLoggingHexUInt32(code, "IoControlCode"));
/* ... handle it ... */
TraceLoggingWrite(g_TgProvider, "IoctlStop",
    TraceLoggingHexUInt32(code, "IoControlCode"),
    TraceLoggingNTStatus(status, "Status"));
```

**Step 2: record and view.** Write a small WPR profile (`.wprp`) that enables the `TgCounter` provider along with CPU sampling, run `tgclient` in a loop, and open the trace. WPA's **Generic Events** table already shows your events with their fields and timestamps, next to the CPU data. No plugin needed to see them.

**Step 3: a WPA plugin (Performance Toolkit SDK).** Generic Events shows raw events. A plugin can **pair** each `IoctlStart` with its `IoctlStop` and produce a proper table: one row per IOCTL with its code, status and duration, graphable over time. That's exactly the kind of plugin the SDK exists for. Its repository has samples and documentation for building a plugin and loading it into WPA.

**Step 4: Profile Explorer.** Use the same trace to look at `tgclient`'s and the driver's CPU samples down to the instruction level, on ARM64.

**Step 5: a WinUI front-end.** A small WinUI 3 app that opens `\\.\TgCounter`, sends `IOCTL_TGCOUNTER_INCREMENT` and `IOCTL_TGCOUNTER_GET` from a background task, and shows the counter value through `DispatcherQueue.TryEnqueue` (§3). Then trace the app's startup with WPR and look at what its UI thread does before the first frame.

What you'd have at the end: a driver with real instrumentation, a custom WPA table, an ARM64 profile read at the instruction level, and a native app that talks to your driver, plus a write-up of what each trace showed. It also gives you something concrete to bring to the open-source repos: you'll have used each of them for real.

---

## 8. How to contribute to a large Microsoft repo

A path that works for any of the four:

1. **Build it and run it.** Follow the README's build instructions on your own machine (or the VM). Problems you hit while building are often worth a docs fix.
2. **Read `CONTRIBUTING.md`** and sign the CLA when the bot asks on your first pull request.
3. **Start with issues, not code:** reproduce open bug reports, add a minimal repro or a trace to an issue that lacks one, or confirm a fix on ARM64. For a repo that isn't accepting code yet (WinUI as of this writing), this is how to take part, and maintainers notice good repros.
4. **First code changes should be small and well-tested:** a bug fix with a test, a docs or sample improvement. Discuss larger changes in an issue first.
5. **Bring evidence:** for performance issues, a trace and before/after numbers (lecture 015 §8).

Your existing open-source work (`dotnet/iot`) is the same skill set: reproduce, fix, test, and explain the change in the PR.

---

## Common mistakes

1. **Thinking WinUI apps aren't Win32 apps.** They are Win32 processes; WinUI is a library inside them.
2. **Touching UI objects from a background thread.** Post to the `DispatcherQueue`.
3. **Awaiting I/O on the UI thread with a blocking call** (`.Result`, `.Wait()`), which freezes the window and can deadlock.
4. **Confusing WinUI 2 and WinUI 3.** WinUI 2 is a control library for UWP XAML (part of Windows); WinUI 3 is the full framework, shipped with the app.
5. **Assuming "on GitHub" means "accepting pull requests."** Check the repo's current contribution policy.
6. **Writing a WPA plugin just to see events.** Generic Events already shows them; write a plugin when you need computed tables.

---

## Self-check questions

1. Is a WinUI 3 app a Win32 app? Explain in terms of processes, threads and windows.
<details><summary>Answer</summary>Yes. It runs as an ordinary Win32 process; its windows are HWNDs owned by a UI thread with a message loop; WinUI is a library loaded into the process that manages XAML content and draws through Direct3D and composition, which DWM combines with other windows.</details>

2. What does "decoupled from the OS" mean for WinUI 3, and what does it buy?
<details><summary>Answer</summary>The framework ships with the app (in the Windows App SDK) instead of being built into Windows. Fixes and features reach users when the app updates, without waiting for a Windows release, and the same app runs back to Windows 10 version 1809.</details>

3. Name four things the Windows App SDK provides besides WinUI 3.
<details><summary>Answer</summary>Any four of: windowing (`AppWindow`), app lifecycle/activation, MRT Core resources, DWriteCore text, notifications, deployment APIs.</details>

4. A background task gets new data. How does it update a WinUI control safely?
<details><summary>Answer</summary>It calls `DispatcherQueue.TryEnqueue(...)` with a delegate; the delegate runs on the window's UI thread, where it can touch the control. The background work itself stays off the UI thread.</details>

5. Packaged vs unpackaged, framework-dependent vs self-contained: what's each choice about?
<details><summary>Answer</summary>Packaged/unpackaged: whether the app is installed as an MSIX package with package identity, or as plain files. Framework-dependent/self-contained: whether it uses the shared WASDK runtime installed on the machine or carries its own copy.</details>

6. What's the contribution status of `microsoft-ui-xaml` as of late October 2026, and how can you take part now?
<details><summary>Answer</summary>Mainline development moved to GitHub (reported Aug 29, 2026), but code changes are limited to Microsoft engineers for now; community code contributions are planned next. You can take part through issues and discussions: reproducing bugs, adding minimal repros or traces, testing on ARM64.</details>

7. What is the Microsoft Performance Toolkit SDK, and when would you write a plugin instead of using Generic Events?
<details><summary>Answer</summary>It's the open-source runtime under Windows Performance Analyzer; it lets you add data sources and tables to WPA. Generic Events shows raw ETW events; write a plugin when you need computed views, such as pairing start/stop events into a per-operation duration table you can graph.</details>

---

## Sources

- [microsoft/WindowsAppSDK](https://github.com/microsoft/WindowsAppSDK) README (formerly Project Reunion; WinUI 3 part of it; Windows 10 1809+; MIT; contributions). Accessed 2026-10-31.
- [microsoft/microsoft-ui-xaml](https://github.com/microsoft/microsoft-ui-xaml) (WinUI). Accessed 2026-10-31.
- Microsoft Learn, [Windows App SDK overview](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/) and [WinUI 3](https://learn.microsoft.com/en-us/windows/apps/winui/winui3/). Accessed 2026-10-31.
- Microsoft Learn, [Windows App SDK deployment overview](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/deploy-overview) (packaged/unpackaged, framework-dependent/self-contained). Accessed 2026-10-31.
- The Register, [Microsoft says it will make WinUI truly open source](https://theregister.com/2025/08/05/microsoft_winui_open_source) (Aug 5, 2025; the four phases). Accessed 2026-10-31.
- Thurrott, [Microsoft Moves WinUI/WASDK Development to GitHub](https://www.thurrott.com/dev/340841/microsoft-moves-winui-wasdk-development-to-github) (Aug 29, 2026). Accessed 2026-10-31.
- Windows Insider Blog, [Windows quality: an update on the commitment we made in March](https://blogs.windows.com/windows-insider/2026/07/31/windows-quality-an-update-on-the-commitment-we-made-in-march/) (Jul 31, 2026). Accessed 2026-10-31.
- [microsoft/profile-explorer](https://github.com/microsoft/profile-explorer) and [microsoft/microsoft-performance-toolkit-sdk](https://github.com/microsoft/microsoft-performance-toolkit-sdk) READMEs. Accessed 2026-10-31.
- Microsoft Learn, [TraceLogging](https://learn.microsoft.com/en-us/windows/win32/tracelogging/trace-logging-portal) (works in kernel-mode drivers). Accessed 2026-10-31.
