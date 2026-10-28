param(
    [Parameter(Mandatory=$true)][string]$Address,
    [ValidateRange(1024,65535)][int]$Port=5173,
    [ValidateRange(1024,65535)][int]$BackendPort=8000
)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskIP=$null
if (-not [System.Net.IPAddress]::TryParse($Address,[ref]$taskIP) -or $taskIP.AddressFamily -ne 'InterNetwork' -or $taskIP.ToString() -ne $Address) {
    throw 'Address must be your teacher computer''s private IPv4 address, such as 192.168.1.20.'
}
$taskBytes=$taskIP.GetAddressBytes()
if (-not ($taskBytes[0] -eq 10 -or ($taskBytes[0] -eq 172 -and $taskBytes[1] -ge 16 -and $taskBytes[1] -le 31) -or ($taskBytes[0] -eq 192 -and $taskBytes[1] -eq 168))) {
    throw 'Only private 10.x.x.x, 172.16-31.x.x or 192.168.x.x addresses are supported.'
}
if (-not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $Address -ErrorAction SilentlyContinue)) {
    throw 'That IP address is not assigned to this computer. Run ipconfig and use its active Wi-Fi IPv4 address.'
}
if (-not $env:TEACHER_PASSWORD -or $env:TEACHER_PASSWORD.Length -lt 12) {throw 'First set $env:TEACHER_PASSWORD to a unique password of at least 12 characters.'}
if (-not $env:APP_SECRET -or $env:APP_SECRET.Length -lt 32) {throw 'First set $env:APP_SECRET to a stable random secret of at least 32 characters.'}
foreach ($taskPort in @($Port,$BackendPort)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $taskPort -ErrorAction SilentlyContinue) {throw "Port $taskPort is already in use. Choose other -Port / -BackendPort values."}
}
$taskChanges=@{
    PUBLIC_ORIGIN="http://${Address}:${Port}"
    API_TARGET="http://127.0.0.1:${BackendPort}"
    ALLOW_LAN_HTTP='true'
    STUDENT_AUTH_MODE='code'
    GOOGLE_CLIENT_ID=''
    GOOGLE_CLIENT_SECRET=''
    TOKEN_ENCRYPTION_KEY=''
}
$taskOld=@{}
foreach ($taskKey in $taskChanges.Keys) {$taskOld[$taskKey]=[Environment]::GetEnvironmentVariable($taskKey,'Process')}
$taskBackend=$null
Push-Location -LiteralPath $taskRoot
try {
    foreach ($taskKey in $taskChanges.Keys) {[Environment]::SetEnvironmentVariable($taskKey,$taskChanges[$taskKey],'Process')}
    $taskPython=(Get-Command python -ErrorAction Stop).Source
    $taskBackend=Start-Process -FilePath $taskPython -ArgumentList @('-m','uvicorn','backend.main:app','--host','127.0.0.1','--port',"$BackendPort",'--workers','1','--ws-max-size','1100000','--ws-max-queue','1') -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskRoot 'lan-backend.log') -RedirectStandardError (Join-Path $taskRoot 'lan-backend-errors.log')
    $taskReady=$false
    for ($taskTry=0;$taskTry -lt 40;$taskTry++) {
        if ($taskBackend.HasExited) {throw 'Backend exited. Check lan-backend-errors.log.'}
        try {Invoke-RestMethod -Uri "http://127.0.0.1:${BackendPort}/api/health" -TimeoutSec 1 | Out-Null;$taskReady=$true;break} catch {Start-Sleep -Milliseconds 250}
    }
    if (-not $taskReady) {throw 'Backend did not become ready. Check lan-backend-errors.log.'}
    Write-Host "Teacher dashboard and student server address: http://${Address}:${Port}"
    Write-Host 'Trusted LAN HTTP only: screenshots and login credentials are unencrypted. Google sign-in/Drive OAuth are disabled for this run.'
    Write-Host 'Use this same address in the teacher browser. On students: enable Allow unencrypted HTTP in the extension.'
    Write-Host "Allow TCP port $Port on your private network if Windows Firewall asks. Do not expose it to the internet."
    & npm.cmd run dev -w web -- --host 0.0.0.0 --port $Port --strictPort
} finally {
    if ($taskBackend -and -not $taskBackend.HasExited) {Stop-Process -Id $taskBackend.Id -ErrorAction SilentlyContinue}
    foreach ($taskKey in $taskChanges.Keys) {[Environment]::SetEnvironmentVariable($taskKey,$taskOld[$taskKey],'Process')}
    Pop-Location
}
