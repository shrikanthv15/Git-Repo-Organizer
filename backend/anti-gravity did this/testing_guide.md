# API Testing Guide

## The PowerShell `curl` Issue
In PowerShell, `curl` is an alias for the cmdlet `Invoke-WebRequest`, which has different syntax than the standard Linux/Mac `curl` tool.
- **Error**: `A parameter cannot be found that matches parameter name 'X'.`
- **Reason**: PowerShell's built-in `curl` alias does not accept the `-X` flag used in standard curl commands.

## Solution 1: Use `curl.exe` (Recommended)
Windows 10 and 11 come with the standard `curl` executable. You can access it by explicitly typing `.exe`. This is the easiest fix as it lets you use the commands exactly as you find them in documentation.

**Correct Command:**
```powershell
curl.exe -X POST https://<your-ngrok-id>.ngrok-free.app/api/test-workflow
```

## Solution 2: Use Native PowerShell Syntax
If you prefer to use the native PowerShell way:
```powershell
Invoke-RestMethod -Method Post -Uri "https://<your-ngrok-id>.ngrok-free.app/api/test-workflow"
```

## Understanding Ngrok URLs
Your ngrok URL (e.g., `https://c4d8808b00ac.ngrok-free.app`) is **dynamic**.
1.  **When it changes**: Every time you stop and restart the `ngrok` command in your terminal.
2.  **What to do**:
    *   Check the `ngrok` terminal window for the line that says `Forwarding`.
    *   Copy the new HTTPS URL.
    *   Replace the URL in your usage (and in your frontend `.env` if you have one connected).

## Troubleshooting `/test-workflow`
The `/api/test-workflow` endpoint connects to the Temporal server.
- **Requirement**: Ensure `temporal server start-dev` is running in a separate terminal.
- **Connection**: It tries to connect to `localhost:7233`. If your backend is running locally, this should work fine.
