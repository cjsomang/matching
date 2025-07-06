import {
    hmacSign,
    generateRsaKeyPair, exportRsaPublicKey,
    rsaEncrypt,
    deriveAesKey, aesEncrypt, aesDecrypt, getAesKey
} from "/static/crypto_utils.js";
export async function renderSelect({
    serverSecretB64,
    anon_id,
    org_json,
    age_json,
    matching_choices_api,
    matching_select_api,
    login_url
}) {
    // 서버에서 전달받은 HMAC에 사용할 serverSecret (변경 없음)
    // 0) salt 값

    const form = document.getElementById('select-form');
    const list = document.getElementById('my-selections');

    const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;

    // console.log(org_json);
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

    // 1) 로그인 시 세션에 저장된 AES 키 꺼내기 · 없으면 재로그인 유도

    // 2) 저장된 encrypted_choices 불러와 복호화해 표시
    async function loadChoices(anon_id) {
        const key = await getAesKey(anon_id);
        const res = await fetch(matching_choices_api);
        if (!res.ok) return;
        const { encrypted_choices } = await res.json();
        if (!encrypted_choices) {
        // list.innerHTML = "<li class='text-muted'>선택한 결과가 없습니다.</li>";
        return;
        }
        const plain = JSON.parse(await aesDecrypt(encrypted_choices, key));
        // list.innerHTML = plain.map(o =>
        // `<li>${o.name}, ${o.age}, ${o.org}</li>`
        // ).join('');
        const rows = document.querySelectorAll('.select-row');

        plain.forEach((choice, i) => {
            if (i >= rows.length) return;
            const row = rows[i];
            row.querySelector('[name=name]').value = choice.name;
            row.querySelector('[name=age]').value = choice.age;
            row.querySelector('[name=org]').value = choice.org;
        });
    }
    await loadChoices(anon_id);

    
    // 3) 폼 제출: 입력값 수집→암호화→서버 저장→화면 갱신
    form.addEventListener('submit', async e => {
        e.preventDefault();
        const key = await getAesKey(anon_id);
        // 3개 입력 그룹에서 데이터 수집
        const rows = document.querySelectorAll('.select-row');
        const choices = [];
        for (let r of rows) {
            const name = r.querySelector('[name=name]').value.trim();
            const age = r.querySelector('[name=age]').value.trim();
            const org = r.querySelector('[name=org]').value.trim();

            const hasAny = name || age || org;
            const hasAll = name && age && org;
            
            // 빈 칸이 있으면 저장 불가
            if (hasAny && !hasAll) {
                alert("후보의 이름, 또래, 마을은 모두 입력하세요.");
                return;
            }
            if (hasAll) {
                choices.push({ name:name, age:age, org:org });
            }
        }
        if (choices.length < 1 || choices.length > 3) {
            alert("후보는 1~3명 입력하세요.");
            return;
        }

        
        const tags = await Promise.all(
            choices.map(c => hmacSign(JSON.stringify(c), serverSecretB64))
        );
        // console.log("tags", tags);  // Base64 문자열 3개?

        const encrypted = await aesEncrypt(JSON.stringify(choices), key);
        const res = await fetch(matching_select_api, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ tags: tags, encrypted_choices: encrypted })
        });
        if (!res.ok) {
            // const text = await res.message();
            // console.error("서버 응답 오류:", text);
            // alert("저장 실패: " + text);
            // return;

            // 가능한 에러 포맷(json or text) 모두 시도해 봅니다.
            let errMsg = await res.text();
            try {
                const obj = await res.json();
                errMsg = obj.message || errMsg;
            } catch {}
            console.error("서버 응답 오류:", errMsg);
            alert("저장 실패: " + errMsg);
            return;
        }
        alert("선택이 저장되었습니다.");
        await loadChoices(anon_id);
    });
};
