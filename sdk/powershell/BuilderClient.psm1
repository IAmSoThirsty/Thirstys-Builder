function New-BuilderClient {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl
    )
    return [PSCustomObject]@{ BaseUrl = $BaseUrl.TrimEnd("/") }
}

function Invoke-BuilderHealth {
    param([Parameter(Mandatory = $true)]$Client)
    return Invoke-RestMethod -Method Get -Uri "$($Client.BaseUrl)/health"
}

function Invoke-BuilderReplay {
    param([Parameter(Mandatory = $true)]$Client)
    return Invoke-RestMethod -Method Get -Uri "$($Client.BaseUrl)/v1/replay"
}

function Invoke-BuilderAudit {
    param([Parameter(Mandatory = $true)]$Client)
    return Invoke-RestMethod -Method Get -Uri "$($Client.BaseUrl)/v1/audit"
}

function Invoke-BuilderExecute {
    param(
        [Parameter(Mandatory = $true)]$Client,
        [Parameter(Mandatory = $true)][string]$RequestId,
        [Parameter(Mandatory = $true)][string]$SubjectId,
        [Parameter(Mandatory = $true)][string]$Operation,
        [Parameter(Mandatory = $true)][string]$Resource,
        [hashtable]$Parameters = @{}
    )
    $body = @{
        request_id = $RequestId
        subject_id = $SubjectId
        operation = $Operation
        resource = $Resource
        parameters = $Parameters
    } | ConvertTo-Json -Depth 10
    return Invoke-RestMethod -Method Post -Uri "$($Client.BaseUrl)/v1/execute" -Body $body -ContentType "application/json"
}

function Invoke-BuilderQuery {
    param(
        [Parameter(Mandatory = $true)]$Client,
        [Parameter(Mandatory = $true)][string]$Query
    )
    $body = @{ query = $Query } | ConvertTo-Json
    return Invoke-RestMethod -Method Post -Uri "$($Client.BaseUrl)/v1/query" -Body $body -ContentType "application/json"
}

function Invoke-BuilderGrpcCompat {
    param(
        [Parameter(Mandatory = $true)]$Client,
        [Parameter(Mandatory = $true)][string]$Method,
        [hashtable]$Payload = @{}
    )
    $body = @{ method = $Method; payload = $Payload } | ConvertTo-Json -Depth 10
    return Invoke-RestMethod -Method Post -Uri "$($Client.BaseUrl)/v1/grpc" -Body $body -ContentType "application/json"
}

Export-ModuleMember -Function New-BuilderClient, Invoke-BuilderHealth, Invoke-BuilderReplay, Invoke-BuilderAudit, Invoke-BuilderExecute, Invoke-BuilderQuery, Invoke-BuilderGrpcCompat
