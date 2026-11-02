using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Showcase.App;
using Showcase.Core;

// Composition root #1 (this process). The Generic Host owns the container,
// constructs SimulationWorker through DI, and calls its ExecuteAsync.
var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddShowcaseCore(options => options.SourceName = "app");
builder.Services.AddHostedService<SimulationWorker>();

using var host = builder.Build();
await host.RunAsync();
