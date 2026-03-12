$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "daily_market_analysis.py" -WorkingDirectory "D:\Gemini\smart_money_hunter 120320260743\smart_money_hunter"
$Trigger = New-ScheduledTaskTrigger -Daily -At 4pm
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "SmartMoneyHunter_Daily" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Runs Smart Money Hunter Market Analysis daily at 16:00" -Force
Write-Host "Scheduled Task 'SmartMoneyHunter_Daily' created successfully for 16:00 daily."
