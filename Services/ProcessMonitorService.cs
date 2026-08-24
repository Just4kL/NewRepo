// Services/ProcessMonitorService.cs
using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Management;
using System.Threading.Tasks;

public class ProcessMonitorService : IDisposable
{
    private ManagementEventWatcher _startWatcher;
    private ManagementEventWatcher _stopWatcher;
    private readonly ConcurrentDictionary<int, (string ProcessName, DateTime StartTime)> _activeSessions = new();
    private readonly HashSet<string> _trackedProcesses = new(); // имена .exe
    private readonly object _lock = new();

    public event Action<GameSession> SessionStarted;
    public event Action<GameSession> SessionEnded;

    public ProcessMonitorService(IEnumerable<string> trackedProcesses)
    {
        foreach (var p in trackedProcesses)
            _trackedProcesses.Add(p.ToLowerInvariant());
    }

    public void Start()
    {
        // Событие запуска процесса
        _startWatcher = new ManagementEventWatcher(
            new WqlEventQuery("SELECT * FROM Win32_ProcessStartTrace"));
        _startWatcher.EventArrived += OnProcessStarted;
        _startWatcher.Start();

        // Событие остановки процесса
        _stopWatcher = new ManagementEventWatcher(
            new WqlEventQuery("SELECT * FROM Win32_ProcessStopTrace"));
        _stopWatcher.EventArrived += OnProcessStopped;
        _stopWatcher.Start();
    }

    private void OnProcessStarted(object sender, EventArrivedEventArgs e)
    {
        string processName = e.NewEvent.Properties["ProcessName"].Value?.ToString();
        int processId = Convert.ToInt32(e.NewEvent.Properties["ProcessID"].Value);

        if (string.IsNullOrEmpty(processName) || !_trackedProcesses.Contains(processName.ToLowerInvariant()))
            return;

        // Проверяем, не запущен ли уже такой же процесс (для простоты — один процесс на игру)
        foreach (var kvp in _activeSessions)
        {
            if (kvp.Value.ProcessName.Equals(processName, StringComparison.OrdinalIgnoreCase))
            {
                // Уже отслеживается, можно игнорировать дубликат или сохранить оба (если поддерживается мультизапуск)
                // Для простоты: не добавляем дубликат
                return;
            }
        }

        var start = DateTime.Now;
        _activeSessions[processId] = (processName, start);

        var session = new GameSession
        {
            SessionGuid = Guid.NewGuid(),
            ProcessName = processName,
            DisplayName = ResolveDisplayName(processName),
            StartTime = start,
            EndTime = null,
            Duration = TimeSpan.Zero
        };
        SessionStarted?.Invoke(session);
    }

    private void OnProcessStopped(object sender, EventArrivedEventArgs e)
    {
        int processId = Convert.ToInt32(e.NewEvent.Properties["ProcessID"].Value);
        if (_activeSessions.TryRemove(processId, out var active))
        {
            var end = DateTime.Now;
            var duration = end - active.StartTime;
            var session = new GameSession
            {
                SessionGuid = Guid.NewGuid(),
                ProcessName = active.ProcessName,
                DisplayName = ResolveDisplayName(active.ProcessName),
                StartTime = active.StartTime,
                EndTime = end,
                Duration = duration
            };
            SessionEnded?.Invoke(session);
        }
    }

    private string ResolveDisplayName(string processName)
    {
        // Здесь можно обращаться к SteamGameLocator для получения названия игры
        return processName.Replace(".exe", "", StringComparison.OrdinalIgnoreCase);
    }

    public void UpdateTrackedProcesses(IEnumerable<string> processes)
    {
        lock (_lock)
        {
            _trackedProcesses.Clear();
            foreach (var p in processes)
                _trackedProcesses.Add(p.ToLowerInvariant());
        }
    }

    public void Dispose()
    {
        _startWatcher?.Stop();
        _stopWatcher?.Stop();
        _startWatcher?.Dispose();
        _stopWatcher?.Dispose();
    }
}