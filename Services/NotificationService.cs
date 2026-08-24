// Services/NotificationService.cs
using System;
using System.Threading.Tasks;
using H.NotifyIcon;

public class NotificationService
{
    private readonly TaskbarIcon _trayIcon;

    public NotificationService(TaskbarIcon trayIcon)
    {
        _trayIcon = trayIcon;
    }

    public async Task ShowSessionEndedAsync(GameSession session)
    {
        await Task.Delay(TimeSpan.FromSeconds(10));
        _trayIcon.ShowNotification(
            $"{session.DisplayName} завершена",
            $"Время в игре: {FormatDuration(session.Duration)}",
            NotificationIcon.Info);
    }

    private string FormatDuration(TimeSpan duration)
    {
        if (duration.TotalHours >= 1)
            return $"{(int)duration.TotalHours} ч {duration.Minutes} мин";
        return $"{duration.Minutes} мин {duration.Seconds} сек";
    }
}