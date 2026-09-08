using System.Collections.ObjectModel;
using System.Windows.Input;
using KodaMate.Models;
using KodaMate.Services;

namespace KodaMate.ViewModels;

/// <summary>
/// ViewModel for the Notifications page.
/// Manages alerts and notifications from Koda.
/// </summary>
public class NotificationsViewModel : BaseViewModel
{
    private readonly IFirebaseService _firebaseService;
    private int _unreadCount;

    /// <summary>
    /// Collection of notifications.
    /// </summary>
    public ObservableCollection<Notification> Notifications { get; } = new();

    /// <summary>
    /// Number of unread notifications.
    /// </summary>
    public int UnreadCount
    {
        get => _unreadCount;
        set => SetProperty(ref _unreadCount, value);
    }

    /// <summary>
    /// Command to refresh notifications.
    /// </summary>
    public ICommand RefreshCommand { get; }

    /// <summary>
    /// Command to mark a notification as read.
    /// </summary>
    public ICommand MarkAsReadCommand { get; }

    /// <summary>
    /// Command to mark all notifications as read.
    /// </summary>
    public ICommand MarkAllReadCommand { get; }

    /// <summary>
    /// Command to dismiss a notification.
    /// </summary>
    public ICommand DismissCommand { get; }

    public NotificationsViewModel(IFirebaseService firebaseService)
    {
        _firebaseService = firebaseService;
        Title = "Notifications";

        RefreshCommand = new AsyncRelayCommand(LoadNotificationsAsync);
        MarkAsReadCommand = new AsyncRelayCommand(MarkAsReadAsync);
        MarkAllReadCommand = new AsyncRelayCommand(MarkAllReadAsync);
        DismissCommand = new RelayCommand(DismissNotification);
    }

    /// <summary>
    /// Called when the page appears.
    /// </summary>
    public override async Task OnAppearingAsync()
    {
        await LoadNotificationsAsync();
    }

    /// <summary>
    /// Loads notifications from Firebase.
    /// </summary>
    private async Task LoadNotificationsAsync()
    {
        if (IsBusy) return;

        try
        {
            IsBusy = true;

            var notifications = await _firebaseService.GetNotificationsAsync();

            Notifications.Clear();
            foreach (var notification in notifications.OrderByDescending(n => n.Timestamp))
            {
                Notifications.Add(notification);
            }

            UpdateUnreadCount();
        }
        catch (Exception ex)
        {
            await Shell.Current.DisplayAlert("Error", $"Failed to load notifications: {ex.Message}", "OK");
        }
        finally
        {
            IsBusy = false;
        }
    }

    /// <summary>
    /// Marks a notification as read.
    /// </summary>
    private async Task MarkAsReadAsync(object? parameter)
    {
        if (parameter is Notification notification && !notification.IsRead)
        {
            await _firebaseService.MarkNotificationReadAsync(notification.Id);
            notification.IsRead = true;
            UpdateUnreadCount();
        }
    }

    /// <summary>
    /// Marks all notifications as read.
    /// </summary>
    private async Task MarkAllReadAsync()
    {
        foreach (var notification in Notifications.Where(n => !n.IsRead))
        {
            await _firebaseService.MarkNotificationReadAsync(notification.Id);
            notification.IsRead = true;
        }
        UpdateUnreadCount();
    }

    /// <summary>
    /// Dismisses a notification.
    /// </summary>
    private void DismissNotification(object? parameter)
    {
        if (parameter is Notification notification)
        {
            Notifications.Remove(notification);
            UpdateUnreadCount();
        }
    }

    /// <summary>
    /// Updates the unread notification count.
    /// </summary>
    private void UpdateUnreadCount()
    {
        UnreadCount = Notifications.Count(n => !n.IsRead);
    }
}
