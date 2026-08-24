// Services/AlarmTimerService.cs
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;

public class AlarmTimerService : IDisposable
{
    private readonly List<AlarmItem> _alarms = new();
    private readonly List<TimerItem> _timers = new();
    private System.Threading.Timer _checkTimer;

    public AlarmTimerService()
    {
        _checkTimer = new System.Threading.Timer(CheckTimers, null, TimeSpan.Zero, TimeSpan.FromSeconds(1));
    }

    private void CheckTimers(object state)
    {
        var now = DateTime.Now;
        foreach (var alarm in _alarms.Where(a => !a.Triggered && a.Time <= now))
        {
            alarm.Triggered = true;
            TriggerAction(alarm.Action);
        }

        foreach (var timer in _timers.Where(t => !t.Triggered && t.EndTime <= now))
        {
            timer.Triggered = true;
            TriggerAction(timer.Action);
        }
    }

    private void TriggerAction(AlarmAction action)
    {
        if (action.ActionType == ActionType.File)
        {
            Process.Start(new ProcessStartInfo(action.Path) { UseShellExecute = true });
        }
        else if (action.ActionType == ActionType.Url)
        {
            Process.Start(new ProcessStartInfo(action.Url) { UseShellExecute = true });
        }
    }

    public void AddAlarm(DateTime time, AlarmAction action) => _alarms.Add(new AlarmItem { Time = time, Action = action });
    public void AddTimer(TimeSpan duration, AlarmAction action) => _timers.Add(new TimerItem { EndTime = DateTime.Now + duration, Action = action });

    public void Dispose() => _checkTimer?.Dispose();
}