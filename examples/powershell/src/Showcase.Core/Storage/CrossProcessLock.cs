namespace Showcase.Core.Storage;

/// <summary>
/// A lock that works across PROCESSES (a C# lock statement only works inside one process).
/// Opening a file with FileShare.None asks the OS for exclusive access; on macOS and Linux
/// .NET implements that with an advisory flock(). A second .NET process trying the same thing
/// gets an IOException, so we retry until the holder disposes its stream.
/// </summary>
internal static class CrossProcessLock
{
    public static IDisposable Acquire(string lockFilePath, TimeSpan timeout)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (true)
        {
            try
            {
                return new FileStream(lockFilePath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
            }
            catch (IOException) when (DateTime.UtcNow < deadline)
            {
                Thread.Sleep(25);
            }
        }
    }
}
