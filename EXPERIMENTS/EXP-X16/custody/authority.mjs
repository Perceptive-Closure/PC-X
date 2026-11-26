import { createHash, createPublicKey, generateKeyPairSync, sign, verify } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';

const authorityPayload = ({ catalogue_sha256, source_commit, frozen_manifest_sha256 }) =>
    Buffer.from(['PCX-X16-authority-v1', catalogue_sha256, source_commit,
        frozen_manifest_sha256, ''].join('\n'), 'utf8');
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const writeJSON = (path, value) => writeFileSync(path, JSON.stringify(value, null, 2) + '\n');

const [mode, catalogue, sourceCommit, manifest, drawFile, authority, drawingSignature] =
    process.argv.slice(2);
if (!/^[a-f0-9]{40}$/.test(sourceCommit ?? '') || !drawingSignature) {
    throw new Error('usage: node authority.mjs sign|check catalogue sourceCommit manifest drawPlan authority drawSignature');
}
const drawBytes = readFileSync(drawFile);
const draw = JSON.parse(drawBytes);
const base = {
    schema: 1,
    catalogue_sha256: digest(readFileSync(catalogue)),
    source_commit: sourceCommit,
    frozen_manifest_sha256: digest(readFileSync(manifest)),
};
for (const key of ['catalogue_sha256', 'source_commit', 'frozen_manifest_sha256']) {
    if (draw[key] !== base[key]) throw new Error('Draw plan does not match the signed source: ' + key);
}
if (mode === 'sign') {
    const { publicKey, privateKey } = generateKeyPairSync('ed25519');
    const public_key_pem = publicKey.export({type:'spki',format:'pem'});
    const signature = sign(null, authorityPayload(base), privateKey).toString('base64');
    writeJSON(authority, { ...base, public_key_pem, signature });
    writeJSON(drawingSignature, {
        schema:1, draw_sha256: digest(drawBytes),
        signature: sign(null, drawBytes, privateKey).toString('base64'),
    });
} else if (mode === 'check') {
    const signed = JSON.parse(readFileSync(authority));
    const signedDraw = JSON.parse(readFileSync(drawingSignature));
    for (const key of Object.keys(base)) {
        if (signed[key] !== base[key]) throw new Error('Authority mismatch ' + key);
    }
    const publicKey = createPublicKey(signed.public_key_pem);
    if (publicKey.asymmetricKeyType !== 'ed25519' ||
        !verify(null, authorityPayload(base), publicKey, Buffer.from(signed.signature, 'base64')) ||
        signedDraw.draw_sha256 !== digest(drawBytes) ||
        !verify(null, drawBytes, publicKey, Buffer.from(signedDraw.signature, 'base64'))) {
        throw new Error('Authority or draw-plan signature invalid');
    }
    console.log('Ed25519 authority + draw plan signatures and exact byte digests verified.');
} else {
    throw new Error('unknown mode');
}
