namespace Showcase.Core.Services;

/// <summary>Scoped: the container creates one per scope, so every scope gets a new Guid.</summary>
public sealed class OperationContext : IOperationContext
{
    public OperationContext(ShowcaseOptions options) => Source = options.SourceName;

    public Guid OperationId { get; } = Guid.NewGuid();

    public string Source { get; }
}
