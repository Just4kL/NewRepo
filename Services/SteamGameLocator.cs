// Services/SteamGameLocator.cs
using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.Win32;

public class SteamGameLocator
{
    public List<SteamGame> GetInstalledGames()
    {
        var games = new List<SteamGame>();
        // Реестр Steam
        using var key = Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam\Apps");
        if (key == null) return games;

        foreach (var subKeyName in key.GetSubKeyNames())
        {
            if (!int.TryParse(subKeyName, out int appId)) continue;
            using var appKey = key.OpenSubKey(subKeyName);
            int installed = Convert.ToInt32(appKey?.GetValue("Installed", 0));
            if (installed == 1)
            {
                string name = ResolveGameName(appId);
                games.Add(new SteamGame { AppId = appId, Name = name });
            }
        }
        return games;
    }

    private string ResolveGameName(int appId)
    {
        // Заглушка: можно получить из appinfo.vdf или из имени папки в steamapps/common
        // В реальном приложении — разобрать VDF файл.
        return $"Steam App {appId}";
    }
}