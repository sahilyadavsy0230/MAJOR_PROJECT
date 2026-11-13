# ==============================================================================
# PRASHANT GROUP WORKFORCE PLATFORM — WINDOWS POSTGRESQL AUTOMATED BACKUP
# ==============================================================================
# Register as daily task:
# Register-ScheduledTask -Action (New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-File C:\path\backup_database.ps1') -Trigger (New-ScheduledTaskTrigger -Daily -At 2am) -TaskName "PrashantGroupDBBackup"
# ==============================================================================

param (
    [string]$DbName = "prashant_group",
    [string]$DbUser = "postgres",
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 5432,
    [string]$BackupDir = "C:\Users\sahil\OneDrive\Attachments\Desktop\PrashantGroup\backups",
    [int]$RetentionDays = 14
)

$ErrorActionPreference = "Stop"
$timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
$logTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$backupFile = Join-Path $BackupDir "${DbName}_backup_${timestamp}.sql"
$env:PGPASSWORD = if ($env:PGPASSWORD) { $env:PGPASSWORD } else { "postgres123" }

Write-Host "[$logTime] Starting PostgreSQL backup for database: $DbName..."

# Locate pg_dump.exe in standard PostgreSQL paths or PATH
$pgDumpPath = "pg_dump"
$standardPaths = @(
    "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
    "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
    "C:\Program Files\PostgreSQL\15\bin\pg_dump.exe"
)
foreach ($p in $standardPaths) {
    if (Test-Path $p) {
        $pgDumpPath = $p
        break
    }
}

try {
    & $pgDumpPath -h $DbHost -p $DbPort -U $DbUser -F p --no-owner --no-privileges $DbName -f $backupFile
    if (Test-Path $backupFile) {
        $fileSize = (Get-Item $backupFile).Length / 1MB
        Write-Host "[$logTime] SUCCESS: Backup created: $backupFile ($([math]::Round($fileSize, 2)) MB)"
    } else {
        throw "Backup file was not created."
    }
} catch {
    Write-Error "[$logTime] FAILED to backup database: $_"
    exit 1
}

# Purge backups older than retention window
$cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -Path $BackupDir -Filter "${DbName}_backup_*.sql" | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
    Write-Host "[$logTime] Removing expired backup: $($_.Name)"
    Remove-Item $_.FullName -Force
}

Write-Host "[$logTime] Daily backup job completed."

