import {
    hmacSign,
    generateRsaKeyPair, exportRsaPublicKey, importRsaPublicKey,
    rsaEncrypt, rsaDecrypt,
    deriveAesKey, aesEncrypt, aesDecrypt, getAesKey
} from "/static/crypto_utils.js";

export async function renderInfo({
    serverSecretB64, anon_id, userSaltB64,
    common_get_myinfo_api,
    common_update_myinfo_api,
    common_delete_myinfo_api,
    org_json,
    age_json
}) {
    const csrf = document.querySelector('#csrf-form [name=csrfmiddlewaretoken]').value;

    // console.log("{{ current_phase }}");
    

    // 1) 로그인 시 세션에 저장된 AES 키 꺼내기 · 없으면 재로그인 유도
    const key = await getAesKey(anon_id);

    // console.log(serverSecretB64);
    // 3) 평문 각각으로 태그 생성 → 일치하는 태그 찾아 표시
    // const serverSecretB64 = "{{ server_secret_b64 }}";
    // const userSaltB64 = "{{ user_salt }}";
    const salt = Uint8Array.from(atob(userSaltB64), c => c.charCodeAt(0));

    const res = await fetch(common_get_myinfo_api);
    const { encrypted_name, encrypted_age, encrypted_org, encrypted_phone, encrypted_privkey, gender } = await res.json();

    // 소속 불러오기
    const orgRes = await fetch(org_json);
    const orgs = await orgRes.json();
    const orgSelects = document.querySelectorAll('.org-select');

    orgSelects.forEach(Select => {
        orgs.forEach(org => {
            const option = document.createElement('option');
            option.value = org;
            option.textContent = org;
            Select.appendChild(option.cloneNode(true));
        });
    });

    // 나이 불러오기
    const ageRes = await fetch(age_json);
    const ages = await ageRes.json();
    const ageSelects = document.querySelectorAll('.age-select');  // 모든 id="age" 요소

    ageSelects.forEach(select => {
        ages.forEach(age => {
            const option = document.createElement('option');
            option.value = age;
            option.textContent = age;
            select.appendChild(option.cloneNode(true));
        });
    });

    // 복호화해서 input에 채움
    document.getElementById("name").value = await aesDecrypt(encrypted_name, key);
    document.getElementById("age").value = await aesDecrypt(encrypted_age, key);
    document.getElementById("org").value = await aesDecrypt(encrypted_org, key);
    // document.getElementById("phone").value = await aesDecrypt(encrypted_phone, key);
    let genderShow;
    if(gender === "M"){
        genderShow = "남";
    }
    else if(gender === "F"){
        genderShow = "여";
    }

    document.getElementById("gender").value = genderShow;

    function formatPhone(raw) {
        raw = raw.replace(/\D/g, '');
        if (raw.length === 11)
            return raw.replace(/(\d{3})(\d{4})(\d{4})/, '$1-$2-$3');
        else if (raw.length === 10)
            return raw.replace(/(\d{3})(\d{3})(\d{4})/, '$1-$2-$3');
        return raw;
    }
    document.getElementById("phone").value = formatPhone(await aesDecrypt(encrypted_phone, key));

    // 3) 입력 중 하이픈 자동 삽입
    const phoneInput = document.getElementById("phone");
    phoneInput.addEventListener("input", () => {
        const raw = phoneInput.value.replace(/\D/g, '');
        let formatted = raw;
        if (raw.length <= 3) {
            formatted = raw;
        } else if (raw.length <= 7) {
            formatted = raw.replace(/(\d{3})(\d+)/, "$1-$2");
        } else {
            formatted = raw.replace(/(\d{3})(\d{4})(\d+)/, "$1-$2-$3");
        }
        phoneInput.value = formatted;
    });

    let privB64;
    try {
        privB64 = await aesDecrypt(encrypted_privkey, key);
        // console.log('복호화된 privB64:', privB64);
    } catch (err) {
        console.error("❌ 개인키 복호화 실패:", err);
        return;
    }
    // const afterenc = await aesEncrypt(privB64, aesKey);



    document.getElementById("myinfo-form").addEventListener("click", async e => {
        if (!e.target.classList.contains('approve-btn')) return;
        e.preventDefault();

        const password = document.getElementById("password").value.trim();
        const pw21 = document.getElementById("password21").value.trim();
        const pw22 = document.getElementById("password22").value.trim();

        if (pw21 && pw21 !== pw22) {
            document.getElementById("msg").textContent = "새 비밀번호가 일치하지 않습니다.";
            return;
        }

        if( pw21 && pw21.length < 6)
        {
            document.getElementById("msg").textContent = "비밀번호는 6글자 이상이어야 합니다.";
            return;
        }


        const form = document.getElementById('myinfo-form');
        // const fd = new FormData(form);

        // fd.append('anon_id', anon_id);
        // fd.append('password', pw);

        // const csrf = fd.get('csrfmiddlewaretoken');

        // const res = await fetch("{% url 'common:login' %}", {
        //     method: 'POST',
        //     credentials: 'same-origin',
        //     // headers: { 'X-CSRFToken': csrf },
        //     body: fd
        // });
        

        // const data = await res.json();
        // if (!res.ok || data.status != "ok"){
        //     document.getElementById("msg").textContent = "저장된 비밀번호와 일치하지 않습니다.";
        //     return;
        // }
        let aesKey = key;
        if (pw21) {
            aesKey = await deriveAesKey(pw21, salt);
        }

        const name = document.getElementById("name").value.trim();
        const age = document.getElementById("age").value.trim();
        const org = document.getElementById("org").value.trim();
        const phone = document.getElementById("phone").value.trim();

        const encrypted_name = await aesEncrypt(name, aesKey);
        const encrypted_age = await aesEncrypt(age, aesKey);
        const encrypted_org = await aesEncrypt(org, aesKey);
        // const encrypted_phone = await aesEncrypt(phone, key);

        const cleanedPhone = phone.replace(/\D/g, '');
        const encrypted_phone = await aesEncrypt(cleanedPhone, aesKey);
        const encrypted_privkey = await aesEncrypt(privB64, aesKey);

        if (!org) {
            document.getElementById("msg").textContent = "마을을 선택해주세요.";
            return;
        }

        // 1-2) profile_tag 암호화 using HAMC
        const profileJson = JSON.stringify({
            name: name,
            age: age,
            org: org
        });
        const profile_tag = await hmacSign(profileJson,serverSecretB64);



        // fd.append('encrypted_name', encrypted_name);
        // fd.append('encrypted_age', encrypted_age);
        // fd.append('encrypted_org', encrypted_org);
        // fd.append('encrypted_phone', encrypted_phone);
        // fd.append('profile_tag', profile_tag);
        // fd.append('password', pw);

        // if (pw21 && pw21 === pw22) {
        //     fd.append('password21', pw21);
        // }

        let payload = {
            encrypted_name, encrypted_age, encrypted_org,
            encrypted_phone, profile_tag, password, encrypted_privkey
        }
        if (pw21 && pw21 === pw22) {
            payload.password21 = pw21;
        }
        // const csrf = fd.get('csrfmiddlewaretoken');
        const res2 = await fetch(common_update_myinfo_api, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
            body: JSON.stringify(payload)
            // body: fd,
        });
        const result = await res2.json();
        console.log("done by here")
        console.log(result.status)

        if(res2.ok && result.status == "ok")
        {
            // session 정보 수정
            const rawKey = await crypto.subtle.exportKey('raw', aesKey);
            const aesKeyB64 = btoa(String.fromCharCode(...new Uint8Array(rawKey)));

            let allKeys = JSON.parse(sessionStorage.getItem('user_keys') || '{}');
            allKeys[anon_id] = aesKeyB64;
            sessionStorage.setItem('user_keys', JSON.stringify(allKeys));
            
            alert("정보가 수정되었습니다.");
            document.getElementById("msg").textContent = "";
        }
        else
        {
            document.getElementById("msg").textContent = result.message;
        }

        
    })

    document.getElementById("myinfo-form").addEventListener("click", async e => {
        if (!e.target.classList.contains('cancel-btn')) return;
        e.preventDefault();
        
        let bDelete = confirm("모든 정보를 삭제하고 탈퇴하시겠습니까?");
        if (!bDelete){ return;}

        const password = document.getElementById("password").value.trim();
        const form = document.getElementById('myinfo-form');
        // const fd = new FormData(form);

        // fd.append('anon_id', anon_id);
        // fd.append('password', pw);

        // const csrf = fd.get('csrfmiddlewaretoken');

        // const res = await fetch("{% url 'common:login' %}", {
        //     method: 'POST',
        //     credentials: 'same-origin',
        //     // headers: { 'X-CSRFToken': csrf },
        //     body: fd
        // });
        

        // const data = await res.json();
        // if (!res.ok || data.status != "ok"){
        //     document.getElementById("msg").textContent = "저장된 비밀번호와 일치하지 않습니다.";
        //     return;
        // }

        let payload = {
            password: password
        }

        // const csrf = fd.get('csrfmiddlewaretoken');
        const res2 = await fetch(common_delete_myinfo_api, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
            body: JSON.stringify(payload)
            // body: fd,
        });
        const result = await res2.json();
        console.log("done by here")
        console.log(result.status)

        if(res2.ok && result.status == "ok")
        {
            alert("회원 탈퇴가 완료되었습니다.");
            document.getElementById("msg").textContent = "";
            window.location.href = result.redirect;
        }
        else
        {
            document.getElementById("msg").textContent = result.message;
        }

        
    })

};
