import {
    hmacSign,
    generateRsaKeyPair, exportRsaPublicKey,
    deriveAesKey, aesEncrypt
} from "/static/crypto_utils.js";

// 서버에서 전달된 secret 값들을 동적으로 받기 위한 인터페이스
export async function renderSignup({
    serverSecretB64,
    userSaltB64,
    signupUrl,
    loginUrl
}) {
    const salt = Uint8Array.from(atob(userSaltB64), c => c.charCodeAt(0));

    const phoneInput = document.getElementById('phone');
    phoneInput.addEventListener('input', () => {
        const raw = phoneInput.value.replace(/\D/g, '');
        let formatted = raw;
        if (raw.length <= 3) formatted = raw;
        else if (raw.length <= 7) formatted = raw.replace(/(\d{3})(\d+)/, '$1-$2');
        else formatted = raw.replace(/(\d{3})(\d{4})(\d+)/, '$1-$2-$3');
        phoneInput.value = formatted;
    });

    // dropdown 목록 불러오기
    const [orgs, ages] = await Promise.all([
        fetch("/static/data/orgs.json").then(res => res.json()),
        fetch("/static/data/ages.json").then(res => res.json()),
    ]);
    const orgSelect = document.getElementById('org');
    const ageSelect = document.getElementById('age');

    orgs.forEach(org => {
        const option = document.createElement('option');
        option.value = org;
        option.textContent = org;
        orgSelect.appendChild(option);
    });

    ages.forEach(age => {
        const option = document.createElement('option');
        option.value = age;
        option.textContent = age;
        ageSelect.appendChild(option);
    });

    const form = document.getElementById('signup-form');
    form.addEventListener('submit', async e => {
        e.preventDefault();
        const fd = new FormData(form);
        const pw = fd.get("password"), pw2 = fd.get("password2");

        if (pw !== pw2) return showMsg("비밀번호가 일치하지 않습니다.");
        if (pw.length < 6) return showMsg("비밀번호는 6글자 이상이어야 합니다.");
        if (!fd.get("org")) return showMsg("마을을 선택해주세요.");

        // 1. HMAC-based 익명 처리
        const userId = fd.get("user_id");
        form.anon_id.value = await hmacSign(userId, serverSecretB64);

        const profileJson = JSON.stringify({
            name: fd.get("name"),
            age: fd.get("age"),
            org: fd.get("org"),
        });
        form.profile_tag.value = await hmacSign(profileJson, serverSecretB64);

        // 2. RSA 키쌍 생성
        const { publicKey, privateKey } = await generateRsaKeyPair();
        form.public_key.value = await exportRsaPublicKey(publicKey);

        // 3. AES 키로 개인키 암호화
        const aesKey = await deriveAesKey(pw, salt);
        const privBuf = await crypto.subtle.exportKey('pkcs8', privateKey);
        const privB64 = btoa(String.fromCharCode(...new Uint8Array(privBuf)));
        form.encrypted_privkey.value = await aesEncrypt(privB64, aesKey);

        // 4. 개인정보 암호화
        form.encrypted_name.value = await aesEncrypt(fd.get("name"), aesKey);
        form.encrypted_age.value = await aesEncrypt(fd.get("age"), aesKey);
        form.encrypted_org.value = await aesEncrypt(fd.get("org"), aesKey);
        const cleanedPhone = fd.get("phone").replace(/\D/g, '');
        form.encrypted_phone.value = await aesEncrypt(cleanedPhone, aesKey);
        form.salt.value = userSaltB64;

        // 5. 전송
        const payload = Object.fromEntries(new FormData(form).entries());
        const csrf = fd.get('csrfmiddlewaretoken');
        const res = await fetch(signupUrl, {
            method: "POST",
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf
            },
            body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (res.ok && result.status === "ok") {
            window.location.href = `${loginUrl}?signup=ok`;
        } else {
            showMsg(result.message || "회원가입 실패");
        }
    });

    function showMsg(msg) {
        document.getElementById("msg").textContent = msg;
    }
}