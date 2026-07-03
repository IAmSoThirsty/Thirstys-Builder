# PowerShell SDK

This SDK uses `Invoke-RestMethod` and preserves server-side authorization
semantics. It is intended for Windows operators and CI scripts.

```powershell
Import-Module ./BuilderClient.psm1
$client = New-BuilderClient -BaseUrl "http://127.0.0.1:8080"
Invoke-BuilderHealth -Client $client
```
