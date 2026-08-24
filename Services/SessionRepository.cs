// Services/SessionRepository.cs
using System;
using System.Collections.Generic;
using System.Data;
using System.Globalization;
using System.IO;
using CsvHelper;
using Microsoft.Data.Sqlite;

public class SessionRepository
{
    private readonly string _connectionString;

    public SessionRepository(string dbPath)
    {
        _connectionString = $"Data Source={dbPath}";
        InitializeDatabase();
    }

    private void InitializeDatabase()
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        var cmd = conn.CreateCommand();
        cmd.CommandText = @"
            CREATE TABLE IF NOT EXISTS Sessions (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                SessionGuid TEXT NOT NULL,
                ProcessName TEXT NOT NULL,
                DisplayName TEXT NOT NULL,
                StartTime TEXT NOT NULL,
                EndTime TEXT,
                DurationTicks INTEGER NOT NULL
            );";
        cmd.ExecuteNonQuery();
    }

    public void AddSession(GameSession session)
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        var cmd = conn.CreateCommand();
        cmd.CommandText = @"
            INSERT INTO Sessions (SessionGuid, ProcessName, DisplayName, StartTime, EndTime, DurationTicks)
            VALUES (@guid, @proc, @name, @start, @end, @ticks);";
        cmd.Parameters.AddWithValue("@guid", session.SessionGuid.ToString());
        cmd.Parameters.AddWithValue("@proc", session.ProcessName);
        cmd.Parameters.AddWithValue("@name", session.DisplayName);
        cmd.Parameters.AddWithValue("@start", session.StartTime.ToString("yyyy-MM-dd HH:mm:ss"));
        cmd.Parameters.AddWithValue("@end", session.EndTime?.ToString("yyyy-MM-dd HH:mm:ss"));
        cmd.Parameters.AddWithValue("@ticks", session.Duration.Ticks);
        cmd.ExecuteNonQuery();
    }

    public List<GameSession> GetAllSessions()
    {
        var result = new List<GameSession>();
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT * FROM Sessions ORDER BY StartTime DESC;";
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            result.Add(new GameSession
            {
                Id = reader.GetInt32(0),
                SessionGuid = Guid.Parse(reader.GetString(1)),
                ProcessName = reader.GetString(2),
                DisplayName = reader.GetString(3),
                StartTime = DateTime.ParseExact(reader.GetString(4), "yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                EndTime = reader.IsDBNull(5) ? null : DateTime.ParseExact(reader.GetString(5), "yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                Duration = TimeSpan.FromTicks(reader.GetInt64(6))
            });
        }
        return result;
    }

    public void ExportToCsv(string filePath)
    {
        var sessions = GetAllSessions();
        using var writer = new StreamWriter(filePath);
        using var csv = new CsvWriter(writer, CultureInfo.InvariantCulture);
        csv.WriteHeader<GameSession>();
        csv.NextRecord();
        foreach (var s in sessions)
        {
            csv.WriteRecord(s);
            csv.NextRecord();
        }
    }
}