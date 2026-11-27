param(
    [string]$Distribution = 'Ubuntu-24.04'
)

$ErrorActionPreference = 'Stop'
$x17Freeze = 'be574f4eaba8a52b50c5604e87075ab4cac81b79'
$x17Root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$x17Stage = Join-Path $x17Root ('.development-' + [guid]::NewGuid().ToString('N'))
[void](New-Item -ItemType Directory -Path $x17Stage)
try {
    $x17Zip = Join-Path $x17Stage 'scoped-source.zip'
    $x17GitRoot = git -C $x17Root rev-parse --show-toplevel
    if ($LASTEXITCODE -ne 0) { throw 'The exact review worktree is unavailable.' }
    git -C $x17GitRoot archive --format=zip "--output=$x17Zip" $x17Freeze -- EXPERIMENTS/EXP-X17/native EXPERIMENTS/EXP-X17/independent/evidence.py EXPERIMENTS/EXP-X17/independent/model.py
    if ($LASTEXITCODE -ne 0) { throw 'The exact development source archive failed.' }
    Expand-Archive -LiteralPath $x17Zip -DestinationPath $x17Stage
    $x17Native = Join-Path $x17Stage 'EXPERIMENTS/EXP-X17'
    $x17Check = Join-Path $x17Root 'review_development.py'
    $x17Mount = wsl.exe -d $Distribution --exec wslpath -a $x17Native
    if ($LASTEXITCODE -ne 0) { throw 'The read-only source mount path is unavailable.' }
    $x17Review = wsl.exe -d $Distribution --exec wslpath -a $x17Check
    if ($LASTEXITCODE -ne 0) { throw 'The review procedure mount path is unavailable.' }
    wsl.exe -d $Distribution --exec /usr/bin/timeout --kill-after=2s 20s /usr/bin/prlimit --as=402653184 --cpu=8 --nproc=128 --fsize=4194304 --nofile=64 /usr/bin/bwrap --unshare-all --unshare-user --disable-userns --cap-drop ALL --clearenv --setenv PATH /usr/bin --setenv HOME /scratch --setenv TMPDIR /scratch --setenv XDG_CACHE_HOME /scratch --ro-bind /usr /usr --symlink usr/bin /bin --symlink usr/lib /lib --symlink usr/lib64 /lib64 --proc /proc --dev /dev --size 16777216 --tmpfs /scratch --ro-bind $x17Mount /source --ro-bind $x17Review /checks/review_development.py --chdir /scratch /usr/bin/python3 -I -B /checks/review_development.py /source /scratch
    if ($LASTEXITCODE -ne 0) { throw 'The offline development check failed.' }
} finally {
    $x17Resolved = (Resolve-Path -LiteralPath $x17Stage).Path
    if ($x17Resolved.StartsWith($x17Root + [IO.Path]::DirectorySeparatorChar) -and (Split-Path $x17Resolved -Leaf) -match '^\.development-[0-9a-f]{32}$') {
        Remove-Item -LiteralPath $x17Resolved -Recurse -Force
    } else {
        throw 'The development staging path failed the scope check.'
    }
}
