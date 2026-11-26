# Fetch and unpack the exact predecessor commit without creating another Git repository.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$Pin = 'a52d45f1b8c0036b1a69b1fc024f95e48d4ce012'
$Ref = 'refs/remotes/origin/codex/exp-x01'
$Origin = (git -C $Root remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0 -or $Origin -notmatch '^https://github\.com/Perceptive-Closure/PC-X(\.git)?$') {
    throw 'The checkout must use the Perceptive-Closure/PC-X HTTPS origin.'
}
$Scratch = Join-Path $Root 'scratch'
$Temp = Join-Path $Scratch 'tmp'
$Extract = Join-Path $Scratch 'x01'
$Archive = Join-Path $Scratch 'x01.zip'
New-Item -ItemType Directory -Path $Scratch,$Temp,$Extract -Force | Out-Null
$OriginalTemp = $env:TEMP
$OriginalTmp = $env:TMP
try {
    $env:TEMP = $Temp
    $env:TMP = $Temp
    git -C $Root -c 'credential.helper=' -c 'credential.helper=!gh auth git-credential' fetch --no-write-fetch-head --no-tags origin "refs/heads/codex/exp-x01:$Ref"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot fetch the pinned X01 branch.' }
    git -C $Root merge-base --is-ancestor $Pin $Ref
    if ($LASTEXITCODE -ne 0) { throw 'The pinned X01 commit is missing from the fetched branch.' }
    git -C $Root archive --format=zip "--output=$Archive" $Pin 'EXPERIMENTS/EXP-X01'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot archive the pinned X01 tree.' }
    Expand-Archive -LiteralPath $Archive -DestinationPath $Extract -Force
    $Model = Join-Path $Extract 'EXPERIMENTS/EXP-X01/src/model.py'
    $Digest = (Get-FileHash -LiteralPath $Model -Algorithm SHA256).Hash
    if ($Digest -ne '6a2b78ea1284ac7ccba1edc0ecc80a9cdbc2d9f2de57a06a6fa216b93a357a2e') {
        throw 'Pinned X01 model digest differs.'
    }
    "Verified X01 $Pin and source digest $Digest"
}
finally {
    $env:TEMP = $OriginalTemp
    $env:TMP = $OriginalTmp
}
