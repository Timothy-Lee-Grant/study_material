using System.Text.Json;
using System.Text.Json.Serialization;

namespace Showcase.Core.Storage;

/// <summary>Serializer settings shared by the storage classes. Enums are stored by name.</summary>
internal static class ShowcaseJson
{
    public static readonly JsonSerializerOptions Indented = new()
    {
        WriteIndented = true,
        Converters = { new JsonStringEnumConverter() },
    };

    public static readonly JsonSerializerOptions Compact = new()
    {
        WriteIndented = false,
        Converters = { new JsonStringEnumConverter() },
    };
}
