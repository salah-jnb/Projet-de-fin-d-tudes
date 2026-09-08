using System.Collections.ObjectModel;
using System.Windows.Input;
using KodaMate.Helpers;
using KodaMate.Models;
using KodaMate.Services;

namespace KodaMate.ViewModels;

/// <summary>
/// ViewModel for the Chat AI page.
/// Envoie les messages via IDistributeurService.SendToN8nAsync → workflow n8n → réponse IA.
/// </summary>
public class ChatViewModel : BaseViewModel
{
    private readonly IDistributeurService _distributeurService;
    private readonly ISessionService _session;
    private readonly IWifiModalService _wifiModal;
    private string _messageText = string.Empty;
    private bool _isTyping;
    private Color _wifiIndicatorColor = Color.FromArgb("#E53935");

    public Color WifiIndicatorColor
    {
        get => _wifiIndicatorColor;
        set => SetProperty(ref _wifiIndicatorColor, value);
    }

    public ICommand OpenWifiNetworksCommand { get; }

    public ObservableCollection<ChatMessage> Messages { get; } = new();

    public string MessageText
    {
        get => _messageText;
        set => SetProperty(ref _messageText, value);
    }

    public bool IsTyping
    {
        get => _isTyping;
        set => SetProperty(ref _isTyping, value);
    }

    public ICommand SendMessageCommand { get; }
    public ICommand TakePhotoCommand { get; }
    public ICommand ClearConversationCommand { get; }

    public ChatViewModel(
        IDistributeurService distributeurService,
        ISessionService session,
        IWifiModalService wifiModal)
    {
        _distributeurService = distributeurService;
        _session = session;
        _wifiModal = wifiModal;
        Title = "Chat avec Koda";

        SendMessageCommand = new AsyncRelayCommand(SendMessageAsync,
            () => !string.IsNullOrWhiteSpace(MessageText));
        TakePhotoCommand = new AsyncRelayCommand(TakePhotoAsync);
        ClearConversationCommand = new RelayCommand(ClearConversation);
        OpenWifiNetworksCommand = new AsyncRelayCommand(OpenWifiNetworksAsync);

        Messages.Add(new ChatMessage
        {
            Content = "Bonjour ! Je suis Koda, votre assistant intelligent. Comment puis-je vous aider ? 🤖",
            IsUserMessage = false,
            Timestamp = DateTime.Now
        });
    }

    private async Task SendMessageAsync()
    {
        if (string.IsNullOrWhiteSpace(MessageText)) return;

        var userText = MessageText.Trim();
        MessageText = string.Empty;

        Messages.Add(new ChatMessage
        {
            Content = userText,
            IsUserMessage = true,
            Timestamp = DateTime.Now
        });

        await SendToN8nAndShowReplyAsync(userText);
    }

    private async Task SendToN8nAndShowReplyAsync(string userText)
    {
        try
        {
            IsTyping = true;

            var questionForN8n = ChatMessageFormatter.AppendPersonSuffix(userText, _session);
            var reply = await _distributeurService.SendToN8nAsync(questionForN8n);

            Messages.Add(new ChatMessage
            {
                Content = string.IsNullOrWhiteSpace(reply)
                    ? "Je n'ai pas pu générer une réponse. Réessayez."
                    : reply,
                IsUserMessage = false,
                Timestamp = DateTime.Now
            });
        }
        catch (HttpRequestException ex)
        {
            var msg = ex.Message.Contains("404", StringComparison.Ordinal)
                ? "⚠️ Workflow n8n introuvable. Vérifiez que n8n tourne sur le PC (pas localhost depuis le téléphone)."
                : "⚠️ Backend inaccessible. Vérifiez le Wi‑Fi et l'URL du serveur.";

            Messages.Add(new ChatMessage
            {
                Content = msg,
                IsUserMessage = false,
                Timestamp = DateTime.Now
            });
        }
        catch (Exception ex)
        {
            Messages.Add(new ChatMessage
            {
                Content = $"Erreur : {ex.Message}",
                IsUserMessage = false,
                Timestamp = DateTime.Now
            });
        }
        finally
        {
            IsTyping = false;
        }
    }

    private async Task TakePhotoAsync()
    {
        if (Shell.Current is null) return;

        if (!await EnsureCameraPermissionsAsync())
            return;

        var choice = await Shell.Current.DisplayActionSheet(
            "Envoyer une photo",
            "Annuler",
            null,
            "Prendre une photo",
            "Choisir dans la galerie");

        if (choice is null or "Annuler")
            return;

        try
        {
            FileResult? result = choice switch
            {
                "Prendre une photo" => await MediaPicker.CapturePhotoAsync(new MediaPickerOptions
                {
                    Title = "Photo pour Koda"
                }),
                "Choisir dans la galerie" => await MediaPicker.PickPhotoAsync(new MediaPickerOptions
                {
                    Title = "Photo pour Koda"
                }),
                _ => null
            };

            if (result is null)
                return;

            var localPath = await CopyToLocalCacheAsync(result);
            if (string.IsNullOrEmpty(localPath))
                return;

            Messages.Add(new ChatMessage
            {
                Content = "📷 Photo envoyée",
                IsUserMessage = true,
                ImagePath = localPath,
                Timestamp = DateTime.Now
            });

            var question = ChatMessageFormatter.AppendPersonSuffix(
                "L'utilisateur a envoyé une photo.",
                _session);

            await SendToN8nAndShowReplyAsync(question);
        }
        catch (FeatureNotSupportedException)
        {
            await Shell.Current.DisplayAlert("Erreur", "Caméra ou galerie non disponible sur cet appareil.", "OK");
        }
        catch (PermissionException)
        {
            await Shell.Current.DisplayAlert(
                "Permission",
                "Autorisez l'accès à la caméra et aux photos dans les paramètres Android.",
                "OK");
        }
        catch (Exception ex)
        {
            await Shell.Current.DisplayAlert("Erreur", ex.Message, "OK");
        }
    }

    private static async Task<bool> EnsureCameraPermissionsAsync()
    {
        var camera = await Permissions.CheckStatusAsync<Permissions.Camera>();
        if (camera != PermissionStatus.Granted)
            camera = await Permissions.RequestAsync<Permissions.Camera>();

        var photos = await Permissions.CheckStatusAsync<Permissions.Photos>();
        if (photos != PermissionStatus.Granted)
            photos = await Permissions.RequestAsync<Permissions.Photos>();

        if (camera != PermissionStatus.Granted)
        {
            if (Shell.Current is not null)
                await Shell.Current.DisplayAlert(
                    "Caméra",
                    "L'accès à la caméra est nécessaire pour prendre une photo.",
                    "OK");
            return false;
        }

        return true;
    }

    private static async Task<string?> CopyToLocalCacheAsync(FileResult result)
    {
        var dest = Path.Combine(FileSystem.CacheDirectory, $"{Guid.NewGuid()}{Path.GetExtension(result.FileName)}");
        await using var src = await result.OpenReadAsync();
        await using var dst = File.OpenWrite(dest);
        await src.CopyToAsync(dst);
        return dest;
    }

    private void ClearConversation()
    {
        Messages.Clear();
        Messages.Add(new ChatMessage
        {
            Content = "Conversation effacée. Comment puis-je vous aider ? 🤖",
            IsUserMessage = false,
            Timestamp = DateTime.Now
        });
    }

    public override async Task OnAppearingAsync()
    {
        UpdateWifiIndicator();
        await Task.CompletedTask;
    }

    public override Task OnDisappearingAsync() => base.OnDisappearingAsync();

    private void UpdateWifiIndicator()
    {
        WifiIndicatorColor = string.IsNullOrEmpty(Preferences.Get("km_wifi_saved_ssid", ""))
            ? Color.FromArgb("#E53935")
            : Color.FromArgb("#43A047");
    }

    private async Task OpenWifiNetworksAsync()
    {
        await _wifiModal.ShowWifiNetworksAsync(() =>
            MainThread.BeginInvokeOnMainThread(UpdateWifiIndicator));
    }
}
