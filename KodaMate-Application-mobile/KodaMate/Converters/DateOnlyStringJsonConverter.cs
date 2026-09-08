using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace KodaMate.Converters;

/// <summary>
/// Parse les dates API "2026-05-19" (sans heure) en date locale, sans décalage UTC.
/// </summary>
public sealed class DateOnlyStringJsonConverter : JsonConverter<DateTime>
{
    public override DateTime Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (reader.TokenType == JsonTokenType.String)
        {
            var raw = reader.GetString();
            if (string.IsNullOrWhiteSpace(raw))
                return default;

            if (DateOnly.TryParse(raw, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dateOnly))
                return dateOnly.ToDateTime(TimeOnly.MinValue);

            if (DateTime.TryParse(raw, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var dt))
                return DateTime.SpecifyKind(dt.Date, DateTimeKind.Unspecified);
        }

        if (reader.TokenType == JsonTokenType.Number)
        {
            try
            {
                return DateTimeOffset.FromUnixTimeMilliseconds(reader.GetInt64()).LocalDateTime.Date;
            }
            catch
            {
                return default;
            }
        }

        return default;
    }

    public override void Write(Utf8JsonWriter writer, DateTime value, JsonSerializerOptions options)
    {
        writer.WriteStringValue(value.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
    }
}
