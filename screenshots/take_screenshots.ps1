$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$base = "http://localhost:8765"
$out = "C:\Users\Nicolas\Documents\GitHub\sharpcirtv2\screenshots"

# Pages to screenshot (path → filename)
$pages = @(
    @{ url = "/incident/1/overview";    name = "01_overview.png" },
    @{ url = "/incident/1/timeline";    name = "02_timeline.png" },
    @{ url = "/incident/1/iocs";        name = "03_iocs.png" },
    @{ url = "/incident/1/tasks";       name = "04_tasks.png" },
    @{ url = "/incident/1/notes";       name = "05_notes.png" },
    @{ url = "/incident/1/activity";    name = "06_activity.png" },
    @{ url = "/incident/1/responders";  name = "07_responders.png" },
    @{ url = "/incident/1/report";      name = "08_report.png" },
    @{ url = "/home";                   name = "09_home.png" }
)

foreach ($p in $pages) {
    $url = "$base$($p.url)"
    $file = "$out\$($p.name)"
    Write-Host "Capturing $url -> $file"
    & $chrome `
        --headless=new `
        --disable-gpu `
        --no-sandbox `
        --window-size=1440,900 `
        --screenshot="$file" `
        "$url"
    Start-Sleep -Milliseconds 500
}

Write-Host "Done."
