# EXP-X07 — Security diagnosis reversal

This experiment tests a bounded diagnosis of offline X.509 verification. The initial condition presents a single locally supplied unrelated root and no intermediate CA. The intervention supplies the approved root and its intermediate for the same signed leaf bytes, hostname, purpose, and fixed time. The four admitted completions cross approved signing-key binding with leaf validity at the specified time. The same generic initial rejection is compatible with both native outcomes.

The independent audit checks the published certificate bytes with Python cryptography. It validates the exact certificate profiles and CA signatures, checks the leaf signature directly against both fixture issuer keys, and reads signed validity dates. It does not run the held-out OpenSSL path-validation command. Both issuers have the same subject name. The stronger native baseline checks the original native error plus native-printed leaf validity, issuer name, AKI and the approved issuer's subject and SKI. Its inference relies on the frozen fixture constraints about well-formed signatures and identifiers. See [OpenSSL verify](https://docs.openssl.org/3.2/man1/openssl-verify/) and [verification options](https://docs.openssl.org/3.2/man1/openssl-verification-options/).

[The protocol](configs/protocol.json) fixes the row and acquisition-cost tables, evidence, command options, baselines, controls, and acceptance criteria. [The execution record](Path.md) binds the protocol, custody and measurement revisions. Root and issuer keys exist only in the seeding process. The seeding script serializes public certificates and the custody record.

## Runtime

Use CPython 3.13 with cryptography already installed and OpenSSL 3.2.4. The Windows run uses `C:/Program Files/Git/usr/bin/openssl.exe`. The checked-in config and an allowlisted subprocess environment fix native command inputs. `-trusted` supplies the only trust anchors for the subprocess. `-untrusted` supplies a local chain-building candidate. The hostname lies under the reserved `.invalid` suffix, and all verification is offline with public fixture PEMs. The commands include fixed-time, hostname, server purpose, strict profile, auth level 2, and root self-signature checks.

## Independent custody

The parent verifies each registered GitHub commit before using its archive. Use an assigned scratch directory on this host for source archives, evidence transport, temporary output, and the private reveal. The script inputs below use full Git commit SHAs. Each `Get-X07Archive` call makes a fresh plain source extraction from GitHub. Its destination must not exist. Record the returned archive SHA-256 in the execution log.

```powershell
function Get-X07Archive($sha, $dest) {
    $known = gh api "repos/Perceptive-Closure/PC-X/commits/$sha" --jq .sha
    if ($LASTEXITCODE -ne 0 -or $known -ne $sha) { throw "GitHub did not verify $sha" }
    $zip = "$dest.zip"
    curl.exe --fail --silent --show-error --location "https://api.github.com/repos/Perceptive-Closure/PC-X/zipball/$sha" --output $zip
    if ($LASTEXITCODE -ne 0) { throw "Archive download failed for $sha" }
    Expand-Archive -LiteralPath $zip -DestinationPath $dest
    $root = @(Get-ChildItem -LiteralPath $dest -Directory)
    if ($root.Count -ne 1 -or (Test-Path -LiteralPath (Join-Path $root[0].FullName '.git'))) {
        throw "Unexpected source archive layout"
    }
    Write-Host "SHA-256 $((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash)"
    $root[0].FullName
}
```

After confirming the executable protocol revision on GitHub, the custodian compares the exact finite proof with the pinned X03 solver and its direct-partition checker. Set `$scratch` to an existing scoped directory. Set `$protocolSha` to the executable freeze from the ledger. Run these commands without opening native results.

```powershell
$x03Sha = 'd85fe1cdb76cbc6d03e58e34f320c4c58a3f243c'
$protocolRoot = Get-X07Archive $protocolSha (Join-Path $scratch 'protocol-source')
$registeredAt = [DateTimeOffset]::UtcNow.ToString('o')
$x03Root = Get-X07Archive $x03Sha (Join-Path $scratch 'x03-source')
$x07 = Join-Path $protocolRoot 'EXPERIMENTS/EXP-X07'
$run = Join-Path $scratch 'x07-run'
$temp = Join-Path $scratch 'tmp'
New-Item -ItemType Directory -Force -Path $temp | Out-Null
$env:TEMP = $temp
$env:TMP = $temp
$openssl = 'C:/Program Files/Git/usr/bin/openssl.exe'
python -B "$x07/run.py" solve --x03-source "$x03Root/EXPERIMENTS/EXP-X03" --out "$scratch/x03-proof.json"
python -B "$x07/run.py" seed --run-dir $run --protocol-commit $protocolSha --protocol-registered-at $registeredAt
python -B "$x07/run.py" diagnose --evidence "$run/evidence" --openssl $openssl --temp $temp
```

The custodian transfers only `$run/evidence` and the commitment digest to the experiment author. The author runs `python -B run.py predict --evidence PATH` and `python -B run.py check --evidence PATH`. The author commits the public evidence and prediction on GitHub. Keep `$run/reveal.json` with the custodian through that check.

The custodian resolves the forecast commit from GitHub and extracts its exact archive. Read the forecast JSON in that archive and verify its SHA-256 against the author's handoff. Use the forecast archive's runner to check the unopened record, then open the outcome from that same archive. Set `$forecastSha` and `$predictionSha` from the verified handoff.

```powershell
$forecastRoot = Get-X07Archive $forecastSha (Join-Path $scratch 'forecast-source')
$forecastRun = Join-Path $forecastRoot 'EXPERIMENTS/EXP-X07'
$pre = Join-Path $forecastRun 'evidence/pre-outcome'
$knownPrediction = (Get-FileHash -LiteralPath "$pre/prediction.json" -Algorithm SHA256).Hash.ToLowerInvariant()
if ($knownPrediction -ne $predictionSha) { throw 'The registered prediction digest differs.' }
$verifiedAt = [DateTimeOffset]::UtcNow.ToString('o')
python -B "$forecastRun/run.py" check --evidence $pre
python -B "$forecastRun/run.py" open --evidence $pre --reveal "$run/reveal.json" --post "$run/post-outcome" --verified-forecast-commit $forecastSha --forecast-verified-at $verifiedAt --verified-prediction-sha256 $predictionSha --openssl $openssl --temp $temp
```

The custodian transfers `$run/post-outcome` after the opening. It contains the reveal, the remote verification receipt, all original stdout and stderr, native exit status, and the scores. The assignment nonce is public after opening and is independent of the certificate signing keys.

## Replay an opened record

From an exact source archive of the terminal evidence commit, run these commands in `EXPERIMENTS/EXP-X07`. Provide an existing scratch-local directory for `$temp` and the authorized OpenSSL binary for `$openssl`. The checker recomputes the forecast from the signed-byte audits, verifies the custody digest, recomputes scores, and optionally reruns the native observations byte for byte.

```powershell
python -B -m unittest discover -s tests -v
python -B run.py check --evidence evidence/pre-outcome --post evidence/post-outcome --replay --openssl $openssl --temp $temp
```

This deterministic, constructed fixture suite supplies exact held-out counts for its eight assignments. The acquisition weights are declared units. The study measures neither operating costs nor the prevalence of a diagnosis across operators, PKIs, or deployments.

To verify the packaged evidence inventory from the experiment directory, check the SHA-256 manifest.

```powershell
foreach ($entry in Get-Content -LiteralPath 'evidence/manifest.sha256') {
    $hash, $relative = $entry -split '  ', 2
    $actual = (Get-FileHash -LiteralPath $relative -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $hash) { throw "Evidence differs at $relative" }
}
```
