// Models/GameSession.cs
public class GameSession
{
    public int Id { get; set; }                 // номер (автоинкремент)
    public Guid SessionGuid { get; set; }       // уникальный ID сессии
    public string ProcessName { get; set; }     // имя процесса (например "ZenlessZoneZero.exe")
    public string DisplayName { get; set; }     // отображаемое имя игры
    public DateTime StartTime { get; set; }     // время запуска
    public DateTime? EndTime { get; set; }      // время завершения
    public TimeSpan Duration { get; set; }      // общее время
    public string StartTimeString => StartTime.ToString("yyyy-MM-dd HH:mm:ss");
}