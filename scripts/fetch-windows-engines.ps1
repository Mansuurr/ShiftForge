param([switch]$KeepDownloads)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$cache = Join-Path $project '.engine-cache'
$bin = Join-Path $project 'bin'

if (Test-Path -LiteralPath $cache) {
    $resolved = (Resolve-Path -LiteralPath $cache).Path
    if (-not $resolved.StartsWith($project, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove cache outside the project: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $cache, $bin | Out-Null

function Download([string]$Url, [string]$Name) {
    $destination = Join-Path $cache $Name
    Write-Host "Downloading $Name..."
    Invoke-WebRequest -Uri $Url -OutFile $destination -UseBasicParsing
    return $destination
}

$ffmpegZip = Download 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' 'ffmpeg.zip'
$ffglitchZip = Download 'https://ffglitch.org/pub/bin/win64/ffglitch-0.10.2-windows-x86_64.zip' 'ffglitch.zip'
$sevenInstaller = Download 'https://www.7-zip.org/a/7z2501-x64.exe' '7zip.exe'

Expand-Archive -LiteralPath $ffmpegZip -DestinationPath (Join-Path $cache 'ffmpeg')
Expand-Archive -LiteralPath $ffglitchZip -DestinationPath (Join-Path $cache 'ffglitch')
$sevenDestination = Join-Path $cache 'sevenzip'
New-Item -ItemType Directory -Path $sevenDestination | Out-Null
$process = Start-Process -FilePath $sevenInstaller -ArgumentList @('/S', "/D=$sevenDestination") `
    -Wait -PassThru -WindowStyle Hidden
if ($process.ExitCode -ne 0) { throw "7-Zip extraction failed with exit code $($process.ExitCode)" }

$ffmpegRoot = Get-ChildItem -LiteralPath (Join-Path $cache 'ffmpeg') -Directory | Select-Object -First 1
$ffglitchRoot = Get-ChildItem -LiteralPath (Join-Path $cache 'ffglitch') -Directory | Select-Object -First 1
Copy-Item -LiteralPath (Join-Path $ffmpegRoot.FullName 'bin\ffmpeg.exe') -Destination (Join-Path $bin 'ffmpeg.exe') -Force
Copy-Item -LiteralPath (Join-Path $ffmpegRoot.FullName 'bin\ffprobe.exe') -Destination (Join-Path $bin 'ffprobe.exe') -Force
Copy-Item -LiteralPath (Join-Path $ffmpegRoot.FullName 'LICENSE') -Destination (Join-Path $bin 'FFmpeg-LICENSE.txt') -Force
Copy-Item -LiteralPath (Join-Path $ffglitchRoot.FullName 'ffgac.exe') -Destination (Join-Path $bin 'ffgac.exe') -Force
Copy-Item -LiteralPath (Join-Path $ffglitchRoot.FullName 'ffedit.exe') -Destination (Join-Path $bin 'ffedit.exe') -Force
Copy-Item -LiteralPath (Join-Path $ffglitchRoot.FullName 'readme.txt') -Destination (Join-Path $bin 'FFglitch-readme.txt') -Force
Copy-Item -LiteralPath (Join-Path $sevenDestination '7z.exe') -Destination (Join-Path $bin '7z.exe') -Force
Copy-Item -LiteralPath (Join-Path $sevenDestination '7z.dll') -Destination (Join-Path $bin '7z.dll') -Force
Copy-Item -LiteralPath (Join-Path $sevenDestination 'License.txt') -Destination (Join-Path $bin '7-Zip-License.txt') -Force

if (-not $KeepDownloads) {
    Remove-Item -LiteralPath $cache -Recurse -Force
}
Write-Host 'Windows conversion engines are ready in bin/.'
