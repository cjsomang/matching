import {
    hmacSign,
    generateRsaKeyPair, exportRsaPublicKey,
    rsaEncrypt,
    deriveAesKey, aesEncrypt, getAesKey
} from "/static/crypto_utils.js";
export async function renderLogin(
    { serverSecretB64 }
)
{
    const form = document.getElementById('login-form');
    const resultDiv = document.getElementById('login-result');

    // 기존의 HMAC 등을 위한 로직은 그대로 유지합니다.
    form.addEventListener('submit', async e => {
        e.preventDefault();

        const userId = form.elements.user_id.value.trim();
        const password = form.elements.password.value;
        if (!userId || !password) {
            resultDiv.textContent = "아이디와 비밀번호를 입력하세요.";
            return;
        }

        // console.log(serverSecretB64);

        // anon_id 생성 (HMAC)
        const anonId = await hmacSign(userId,serverSecretB64);
        // document.getElementById('anon_id').value = anonId;
   
        
        const fd = new FormData(form);
        const csrf = fd.get('csrfmiddlewaretoken');

        fd.append('anon_id', anonId);
        fd.append('password', password);

        try {
            const res = await fetch(form.action, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'X-CSRFToken': csrf },
                body: fd
            });
            const contentType = res.headers.get('Content-Type') || '';
            if (!contentType.includes('application/json')) {
                resultDiv.textContent = "서버에서 JSON이 아닌 응답을 보냈습니다.";
                return;
            }


            const data = await res.json();
            if (res.ok && data.status === 'ok') {
                const userSaltB64 = data.user_salt;
                const salt = Uint8Array.from(atob(userSaltB64), c => c.charCodeAt(0));

                // local storage에 user key 저장
                const aesKey = await deriveAesKey(password, salt);
                const rawKey = await crypto.subtle.exportKey('raw', aesKey);
                const aesKeyB64 = btoa(String.fromCharCode(...new Uint8Array(rawKey)));

                let allKeys = JSON.parse(sessionStorage.getItem('user_keys') || '{}');
                allKeys[anonId] = aesKeyB64;
                sessionStorage.setItem('user_keys', JSON.stringify(allKeys));

                // for salt debuging
                // const saltstring = btoa(String.fromCharCode(...new Uint8Array(salt)));
                // console.log('salt from server:', saltstring);
                // console.log('encoded AES key:', aesKeyB64);
                
                // 로그인 후 redirect
                window.location.href = data.redirect;
            } else {
                resultDiv.textContent = data.message || "로그인 실패";
            }
        } catch (err) {
            console.error("❌ 네트워크 오류:", err);
            resultDiv.textContent = "네트워크 오류가 발생했습니다.";
        }
    });
};