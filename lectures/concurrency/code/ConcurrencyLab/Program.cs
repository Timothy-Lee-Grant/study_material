// ConcurrencyLab - concurrency lecture 003.
// Run:  dotnet run -c Release -- <experiment> [n]
//   order               : what runs on which thread, and when, for an async call with and without await
//   threads <n>         : n OS threads, each blocked waiting for "data"   (thread-per-request model)
//   tasks <n>           : n async methods, each suspended awaiting "data" (async model)
//   pool                : how the thread pool grows when its threads block
using System.Diagnostics;
using System.Runtime.CompilerServices;

static class Program
{
    static int Tid => Environment.CurrentManagedThreadId;

    static async Task<int> Main(string[] args)
    {
        string exp = args.Length > 0 ? args[0] : "order";
        int n = args.Length > 1 ? int.Parse(args[1]) : 5000;
        switch (exp)
        {
            case "order":   await Order(); break;
            case "threads": Threads(n); break;
            case "tasks":   await Tasks(n); break;
            case "pool":    Pool(); break;
            default: Console.WriteLine("unknown experiment"); return 1;
        }
        return 0;
    }

    // ------------------------------------------------------------------ order
    static async Task<int> ReadAsync(string label)
    {
        Console.WriteLine($"  [{label}] ReadAsync starts on thread {Tid} (runs synchronously so far)");
        await Task.Delay(100);   // the first await of something NOT finished: method suspends here
        Console.WriteLine($"  [{label}] ReadAsync resumes on thread {Tid} (a thread-pool thread)");
        return 42;
    }

    static async Task Order()
    {
        Console.WriteLine($"Main on thread {Tid}");

        Console.WriteLine("1) Call without await:");
        Task<int> t = ReadAsync("A");
        Console.WriteLine($"  call returned a Task, IsCompleted={t.IsCompleted}; caller continues on thread {Tid}");
        Console.WriteLine("  caller does other work here...");
        int a = await t;
        Console.WriteLine($"  awaited later: result {a}, now on thread {Tid}");

        Console.WriteLine("2) Call with await:");
        int b = await ReadAsync("B");
        Console.WriteLine($"  result {b}, now on thread {Tid}");
    }

    // ------------------------------------------------------------------ memory
    static void Report(string label, Stopwatch sw)
    {
        GC.Collect(); GC.WaitForPendingFinalizers(); GC.Collect();
        var p = Process.GetCurrentProcess(); p.Refresh();
        Console.WriteLine($"{label,-28} OS threads: {p.Threads.Count,5}   reserved (virtual): {p.VirtualMemorySize64 / 1073741824.0,6:F1} GB   resident: {p.WorkingSet64 / 1048576.0,6:F1} MB   " +
                          $"GC heap: {GC.GetTotalMemory(false) / 1048576.0,5:F2} MB   t={sw.ElapsedMilliseconds} ms");
    }

    static void Threads(int n)
    {
        var sw = Stopwatch.StartNew();
        Report("before", sw);
        var dataArrived = new ManualResetEventSlim(false);   // stands in for "socket has data"
        var started = new CountdownEvent(n);
        var threads = new List<Thread>(n);
        for (int i = 0; i < n; i++)
        {
            int id = i;
            var th = new Thread(() =>
            {
                var buffer = new byte[256];        // this request's local state
                started.Signal();
                dataArrived.Wait();                // BLOCKS: the OS thread sleeps here
                buffer[0] = (byte)id;
            });
            th.IsBackground = true;
            th.Start();
            threads.Add(th);
        }
        started.Wait();
        Report($"{n} threads blocked waiting", sw);
        dataArrived.Set();
        foreach (var th in threads) th.Join();
        Thread.Sleep(1000);                        // let exited threads be cleaned up
        Report("after all finished", sw);
    }

    static async Task HandleRequestAsync(int id, Task<int> dataArrived)
    {
        var buffer = new byte[256];                // same local state
        int value = await dataArrived;             // SUSPENDS: no thread is held
        buffer[0] = (byte)(id + value);
    }

    static async Task Tasks(int n)
    {
        var sw = Stopwatch.StartNew();
        Report("before", sw);
        var tcs = new TaskCompletionSource<int>(TaskCreationOptions.RunContinuationsAsynchronously);
        var all = new Task[n];
        for (int i = 0; i < n; i++) all[i] = HandleRequestAsync(i, tcs.Task);
        Report($"{n} async methods suspended", sw);
        Console.WriteLine($"  one suspended method's state machine type: {StateMachineSize()}");
        tcs.SetResult(1);
        await Task.WhenAll(all);
        Report("after all finished", sw);
    }

    static string StateMachineSize()
    {
        // Measure the heap bytes allocated by starting one more suspended call.
        var tcs = new TaskCompletionSource<int>();
        _ = HandleRequestAsync(0, tcs.Task);       // warm up (JIT)
        long before = GC.GetAllocatedBytesForCurrentThread();
        _ = HandleRequestAsync(0, tcs.Task);
        long after = GC.GetAllocatedBytesForCurrentThread();
        return $"{after - before} bytes allocated per suspended call (state machine box + its 256-byte buffer + continuation)";
    }

    // ------------------------------------------------------------------ pool
    static void Pool()
    {
        ThreadPool.GetMinThreads(out int minWorkers, out int minIo);
        Console.WriteLine($"processors: {Environment.ProcessorCount}, pool min worker threads: {minWorkers}");
        Console.WriteLine($"pool threads at start: {ThreadPool.ThreadCount}");

        var gate = new ManualResetEventSlim(false);
        var sw = Stopwatch.StartNew();
        for (int i = 0; i < 64; i++)
            ThreadPool.QueueUserWorkItem(_ => gate.Wait());   // BAD: blocks a pool thread
        for (int s = 0; s <= 6; s++)
        {
            Console.WriteLine($"t={sw.ElapsedMilliseconds,5} ms  pool threads: {ThreadPool.ThreadCount,3}   queued items waiting for a thread: {ThreadPool.PendingWorkItemCount,3}");
            Thread.Sleep(1000);
        }
        gate.Set();
    }
}
