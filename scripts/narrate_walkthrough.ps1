$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskVideo = Join-Path $taskRoot 'release/video'
$taskScenes = Get-Content -LiteralPath (Join-Path $taskVideo 'scenes.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$taskSpeaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$taskSpeaker.SelectVoice('Microsoft Zira Desktop')
$taskSpeaker.Rate = 1
try {
    for ($taskIndex = 0; $taskIndex -lt $taskScenes.Count; $taskIndex++) {
        $taskWav = Join-Path $taskVideo ('scene-{0:D2}.wav' -f ($taskIndex + 1))
        $taskSpeaker.SetOutputToWaveFile($taskWav)
        $taskSpeaker.Speak($taskScenes[$taskIndex].narration)
        $taskSpeaker.SetOutputToNull()
    }
} finally {
    $taskSpeaker.Dispose()
}
Write-Output 'Created offline narration for all walkthrough scenes.'
