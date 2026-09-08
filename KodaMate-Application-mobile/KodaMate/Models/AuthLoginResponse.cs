using System.Text.Json.Serialization;

namespace KodaMate.Models;

public class AuthLoginResponse
{
    [JsonPropertyName("status")]
    public string? Status { get; set; }

    [JsonPropertyName("data")]
    public AuthLoginData? Data { get; set; }
}

public class AuthLoginData
{
    [JsonPropertyName("idproduit")]
    public int Idproduit { get; set; }

    [JsonPropertyName("emailclient")]
    public string? Emailclient { get; set; }

    [JsonPropertyName("idkoda")]
    public string? Idkoda { get; set; }
}
