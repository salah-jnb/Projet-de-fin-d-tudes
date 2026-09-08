using System.Collections.ObjectModel;
using System.Windows.Input;
using KodaMate.Helpers;
using KodaMate.Models;
using KodaMate.Services;

namespace KodaMate.ViewModels;

public class HistoryViewModel : BaseViewModel
{
    private readonly IDistributeurService _distributeurService;
    private string _selectedFilter = "Tous";
    private DateTime _customFilterDate = DateTime.Today;
    private string _searchQuery = string.Empty;

    public ObservableCollection<ConversationHistoryEntry> Entries { get; } = new();

    public IReadOnlyList<string> FilterOptions { get; } =
    [
        "Tous",
        "Aujourd'hui",
        "Hier",
        "Cette semaine",
        "Choisir une date"
    ];

    public string SelectedFilter
    {
        get => _selectedFilter;
        set
        {
            if (SetProperty(ref _selectedFilter, value))
            {
                OnPropertyChanged(nameof(ShowCustomDatePicker));
                _ = LoadConversationsAsync();
            }
        }
    }

    public DateTime CustomFilterDate
    {
        get => _customFilterDate;
        set
        {
            if (SetProperty(ref _customFilterDate, value.Date))
                _ = LoadConversationsAsync();
        }
    }

    public bool ShowCustomDatePicker => SelectedFilter == "Choisir une date";

    public string SearchQuery
    {
        get => _searchQuery;
        set
        {
            if (SetProperty(ref _searchQuery, value))
                ApplySearchFilter();
        }
    }

    public ICommand RefreshCommand { get; }

    public HistoryViewModel(IDistributeurService distributeurService)
    {
        _distributeurService = distributeurService;
        Title = "Historique";
        RefreshCommand = new AsyncRelayCommand(LoadConversationsAsync);
    }

    public override async Task OnAppearingAsync() => await LoadConversationsAsync();

    private bool _isLoading;
    private List<ConversationBackend> _loaded = [];

    private async Task LoadConversationsAsync()
    {
        if (_isLoading) return;

        try
        {
            _isLoading = true;
            IsBusy = true;

            var (apiFrom, apiTo) = ResolveApiDateRange();
            var backend = await _distributeurService.GetAllConversationsAsync(apiFrom, apiTo);

            var (filterFrom, filterTo) = ConversationDateHelper.ResolveFilterRange(SelectedFilter, CustomFilterDate);
            _loaded = backend
                .Where(c => ConversationDateHelper.IsInRange(ConversationDateHelper.ToDateOnly(c), filterFrom, filterTo))
                .OrderByDescending(c => ConversationDateHelper.ToDateOnly(c))
                .ThenByDescending(c => c.Idconv)
                .ToList();

            ApplySearchFilter();
        }
        catch (Exception ex)
        {
            if (Shell.Current is not null)
                await Shell.Current.DisplayAlert("Erreur",
                    $"Impossible de charger l'historique : {ex.Message}", "OK");
        }
        finally
        {
            _isLoading = false;
            IsBusy = false;
        }
    }

    private (DateTime? from, DateTime? to) ResolveApiDateRange()
    {
        var (from, to) = ConversationDateHelper.ResolveFilterRange(SelectedFilter, CustomFilterDate);
        if (!from.HasValue)
            return (null, null);
        return (from.Value.ToDateTime(TimeOnly.MinValue), to!.Value.ToDateTime(TimeOnly.MinValue));
    }

    private void ApplySearchFilter()
    {
        Entries.Clear();
        var filtered = string.IsNullOrWhiteSpace(SearchQuery)
            ? _loaded
            : _loaded.Where(c =>
                (c.Question ?? "").Contains(SearchQuery, StringComparison.OrdinalIgnoreCase) ||
                (c.Reponce ?? "").Contains(SearchQuery, StringComparison.OrdinalIgnoreCase) ||
                (c.TypeDeQuestion ?? "").Contains(SearchQuery, StringComparison.OrdinalIgnoreCase));

        DateOnly? lastDay = null;
        foreach (var conv in filtered)
        {
            var day = ConversationDateHelper.ToDateOnly(conv);
            if (day != lastDay)
            {
                lastDay = day;
                Entries.Add(new ConversationHistoryEntry
                {
                    IsDateHeader = true,
                    DisplayDate = ConversationDateHelper.FormatDayHeader(day)
                });
            }

            Entries.Add(new ConversationHistoryEntry
            {
                IsDateHeader = false,
                Idconv = conv.Idconv,
                Question = conv.Question,
                Reponce = conv.Reponce,
                MessageDateLabel = ConversationDateHelper.FormatMessageDate(day)
            });
        }
    }
}
