using System.Globalization;
using KodaMate.Models;

namespace KodaMate.Helpers;

public static class ConversationDateHelper
{
    private static readonly CultureInfo Fr = CultureInfo.GetCultureInfo("fr-FR");

    public static DateOnly ToDateOnly(ConversationBackend conversation)
    {
        var d = conversation.Date;
        if (d == default)
            return DateOnly.MinValue;
        return DateOnly.FromDateTime(d.Date);
    }

    public static string FormatDayHeader(DateOnly date)
    {
        var today = DateOnly.FromDateTime(DateTime.Today);
        if (date == today) return "Aujourd'hui";
        if (date == today.AddDays(-1)) return "Hier";
        return date.ToString("dddd d MMMM yyyy", Fr);
    }

    /// <summary>Date du message (l'API ne fournit pas l'heure).</summary>
    public static string FormatMessageDate(DateOnly date)
    {
        if (date == DateOnly.MinValue)
            return string.Empty;
        return date.ToString("d MMMM yyyy", Fr);
    }

    public static bool IsInRange(DateOnly date, DateOnly? from, DateOnly? to)
    {
        if (from.HasValue && date < from.Value)
            return false;
        if (to.HasValue && date > to.Value)
            return false;
        return true;
    }

    public static (DateOnly? from, DateOnly? to) ResolveFilterRange(
        string selectedFilter,
        DateTime customFilterDate)
    {
        var today = DateOnly.FromDateTime(DateTime.Today);
        return selectedFilter switch
        {
            "Aujourd'hui" => (today, today),
            "Hier" => (today.AddDays(-1), today.AddDays(-1)),
            "Cette semaine" => (StartOfWeek(today), today),
            "Choisir une date" => (DateOnly.FromDateTime(customFilterDate.Date), DateOnly.FromDateTime(customFilterDate.Date)),
            _ => (null, null)
        };
    }

    private static DateOnly StartOfWeek(DateOnly today)
    {
        var dow = (int)today.DayOfWeek;
        var offset = (7 + dow - (int)DayOfWeek.Monday) % 7;
        return today.AddDays(-offset);
    }
}
