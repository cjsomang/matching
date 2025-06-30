// crypto_utils.js
// Utility functions for cryptographic operations using Web Crypto API

// 방법 1 : HMAC
/**
 * Generate HMAC signature for a message.
 * @param {string} message - The message to sign.
 * @param {string} b64Secret - Base64-encoded secret key.
 * @returns {Promise<string>} Base64-encoded signature.
 */
export async function hmacSign(message, b64Secret) {
    const secret = Uint8Array.from(atob(b64Secret), c => c.charCodeAt(0));
    const key = await crypto.subtle.importKey(
        'raw', secret,
        { name: 'HMAC', hash: 'SHA-256' },
        false, ['sign']
    );
    const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
    return btoa(String.fromCharCode(...new Uint8Array(sig)));
}



// 방법 2 : RSA-OAEP
/**
 * Generate an RSA-OAEP key pair.
 * @returns {Promise<{publicKey: CryptoKey, privateKey: CryptoKey}>}
 */
export async function generateRsaKeyPair() {
    return crypto.subtle.generateKey(
        { name: 'RSA-OAEP', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' },
        true, ['encrypt', 'decrypt']
    );
}

/**
 * Export RSA public key to PEM format.
 * @param {CryptoKey} publicKey
 * @returns {Promise<string>} PEM-formatted public key
 */
export async function exportRsaPublicKey(publicKey) {
    const spki = await crypto.subtle.exportKey('spki', publicKey);
    const b64 = btoa(String.fromCharCode(...new Uint8Array(spki)));
    const lines = b64.match(/.{1,64}/g).join('\n');
    return `-----BEGIN PUBLIC KEY-----\n${lines}\n-----END PUBLIC KEY-----`;
}

/**
 * Import RSA public key from PEM format.
 * @param {string} pem
 * @returns {Promise<CryptoKey>}
 */
export async function importRsaPublicKey(pem) {
    const b64 = pem.replace(/-----[^-]+-----|\s+/g, '');
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    return crypto.subtle.importKey(
        'spki', bytes.buffer,
        { name: 'RSA-OAEP', hash: 'SHA-256' },
        false, ['encrypt']
    );
}

/**
 * RSA-OAEP encrypt data with given public key.
 * @param {CryptoKey} publicKey
 * @param {Uint8Array} data
 * @returns {Promise<Uint8Array>} ciphertext
 */
export async function rsaEncrypt(publicKey, data) {
    const ct = await crypto.subtle.encrypt(
        { name: 'RSA-OAEP' }, publicKey, new TextEncoder().encode(data)
    );
    return btoa(String.fromCharCode(...new Uint8Array(ct)))
}

/**
 * RSA-OAEP decrypt ciphertext with given private key.
 * @param {CryptoKey} privateKey
 * @param {string} b64
 * @returns {Promise<Uint8Array>} plaintext
 */
export async function rsaDecrypt(privateKey, b64) {
    // Decoding to Array
    const binary = atob(b64);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    // const cyphertext = bytes;

    const pt = await crypto.subtle.decrypt(
        { name: 'RSA-OAEP' }, privateKey, bytes.buffer
    );
    return new Uint8Array(pt);
}


// 방법 3 AES-GCM
/**
 * Derive an AES-GCM key from a password and salt using PBKDF2.
 * @param {string} password
 * @param {string} b64Salt - Base64-encoded salt
 * @returns {Promise<CryptoKey>}
 */
export async function deriveAesKey(password, salt) {
    // const salt = Uint8Array.from(atob(b64Salt), c => c.charCodeAt(0));
    const baseKey = await crypto.subtle.importKey(
        'raw', new TextEncoder().encode(password),
        { name: 'PBKDF2' }, false, ['deriveKey']
    );
    return crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
        baseKey,
        { name: 'AES-GCM', length: 256 },
        true,
        ['encrypt', 'decrypt']
    );
}

/**
 * Encrypt plaintext string with AES-GCM key.
 * @param {string} plaintext
 * @param {CryptoKey} key
 * @returns {Promise<string>} Base64(IV + ciphertext)
 */
export async function aesEncrypt(plaintext, key) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ct = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv }, key, new TextEncoder().encode(plaintext)
    );
    const combined = new Uint8Array(iv.byteLength + ct.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(ct), iv.byteLength);
    return btoa(String.fromCharCode(...combined));
}

/**
 * Decrypt Base64(IV + ciphertext) with AES-GCM key.
 * @param {string} b64Data
 * @param {CryptoKey} key
 * @returns {Promise<string>} plaintext
 */
export async function aesDecrypt(b64Data, key) {
    const combined = Uint8Array.from(atob(b64Data.trim()), c => c.charCodeAt(0));
    const iv = combined.slice(0, 12);
    const ct = combined.slice(12);
    const pt = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv }, key, ct.buffer
    );
    return new TextDecoder().decode(pt);
}

/**
 * get aes key
 * @param {string} anon_id
 * @returns {CryptoKey} plaintext
 */
export async function getAesKey(anon_id) {
    const allKeys = JSON.parse(sessionStorage.getItem('user_keys') || '{}');
    const encryptedPriv = allKeys[anon_id];
    if (!encryptedPriv) {
        alert("세션 만료: 다시 로그인해주세요.");
        window.location.href = "{% url 'common:login' %}";
        throw new Error("AES 키 없음");
    }
    const raw = Uint8Array.from(atob(encryptedPriv), c => c.charCodeAt(0));
    return crypto.subtle.importKey('raw', raw.buffer, { name: 'AES-GCM' }, true, ['encrypt', 'decrypt']);
}