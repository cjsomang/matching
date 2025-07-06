// static/js/results.js
import {
    hmacSign,
    generateRsaKeyPair, exportRsaPublicKey, importRsaPublicKey,
    rsaEncrypt, rsaDecrypt,
    deriveAesKey, aesEncrypt, aesDecrypt, getAesKey
} from "/static/crypto_utils.js";

export async function renderResults({
    anon_id, serverSecretB64, phase, gender,
    matching_choices_api, matching_results_api, matching_grant_contact_api, 
    matching_cancel_grant_api, matching_get_granted_by_me_api,
    matching_get_granted_contact_api, common_get_myinfo_api
}) {
    const csrf = document.querySelector('#csrf-form [name=csrfmiddlewaretoken]').value;
    
    // 1) 로그인 시 세션에 저장된 AES 키 꺼내기 · 없으면 재로그인 유도
    const key = await getAesKey(anon_id);

    // 2) 서버에서 encrypted_choices 받아와 복호화
    const resEnc = await fetch(matching_choices_api);
    const { encrypted_choices } = await resEnc.json();
    if (!encrypted_choices) {
        document.getElementById('no-matches').textContent = "내가 선택한 기록이 없습니다.";
        return;
    }
    const plainChoices = JSON.parse(await aesDecrypt(encrypted_choices, key));

    // 3-1) 서버가 준 매칭 리스트
    const res = await fetch(matching_results_api);
    const { matches } = await res.json();
    if (!matches.length) {
        document.getElementById('no-matches').textContent = "매칭된 상대가 없습니다.";
        return;
    }

    // 3-2) 내가 승인한 상대 리스트 받아오기
    const resMe = await fetch(matching_get_granted_by_me_api);
    const grantedByMe = (await resMe.json()).granted.map(g => g.to_user); // ["anonId1", "anonId2"]

    // 3-2) 나를 승인한 상대 리스트 받아오기
    const resThem = await fetch(matching_get_granted_contact_api);
    const grantedToMeList = (await resThem.json()).granted; // [{ from_user: anonId, reencrypted_phone }, ...]
    const grantedToMeMap = {};
    for (const g of grantedToMeList) {
        grantedToMeMap[g.from_user] = g.reencrypted_phone;
    }

    // 내 연락처 받아오기
    const res_in = await fetch(common_get_myinfo_api);
    const mydata = await res_in.json();

    // console.log('my enc phone: ', mydata.encrypted_phone);

    if (!mydata.encrypted_phone || mydata.encrypted_phone.length < 20) {
        throw new Error("연락처 암호문 형식이 이상함");
    }

    // 3-3) 내 비밀키 import
    let privB64;
    try {
        privB64 = await aesDecrypt(mydata.encrypted_privkey, key);
        // console.log('복호화된 privB64:', privB64);
    } catch (err) {
        console.error("❌ 개인키 복호화 실패:", err);
        return;
    }
    // console.log('내 priv 키:', privKey);
    const privBytes = Uint8Array.from(atob(privB64), c => c.charCodeAt(0));
    // importKey로 RSA‑OAEP privateKey 복원
    const privateKey = await crypto.subtle.importKey(
        'pkcs8',
        privBytes.buffer,
        { name: 'RSA-OAEP', hash: 'SHA-256' },
        false,
        ['decrypt']
    );
    // console.log('복원된 RSA privateKey:', privateKey);

    function formatPhone(raw) {
        raw = raw.replace(/\D/g, '');
        if (raw.length === 11)
            return raw.replace(/(\d{3})(\d{4})(\d{4})/, '$1-$2-$3');
        else if (raw.length === 10)
            return raw.replace(/(\d{3})(\d{3})(\d{4})/, '$1-$2-$3');
        return raw;
    }

    // 3) 평문 각각으로 태그 생성 → 일치하는 태그 찾아 표시
    
    const list = document.getElementById('match-list');
    list.innerHTML = '';
    let bAppend = false;
    for (let choice of plainChoices) {
        const tag = await hmacSign(JSON.stringify(choice), serverSecretB64);
        const cand = matches.find(m => m.profile_tag === tag);
        if (!cand) continue;

        const anonId = cand.candidate_id;
        const iApproved = grantedByMe.includes(anonId);
        const theyApproved = anonId in grantedToMeMap;

        const li = document.createElement('li');

        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.dataset.anon = cand.candidate_id;
        li.dataset.pubkey = cand.public_key;

        let contactHTML = '';
        let buttonHTML = '';
        let cancelButtonHTML = '';


        // console.log(phase);
        // console.log(gender);


        // 승인 여부에 따라 버튼 대신 연락처 채워넣기
        // 나와 상대방이 모두 승인 -> 연락처 공개
        // 나만 승인 -> 승인 버튼 비활성화
        if (iApproved && theyApproved && phase === "final") {
            const phoneBytes = await rsaDecrypt(privateKey, grantedToMeMap[anonId]);
            const phone = new TextDecoder().decode(phoneBytes);
            contactHTML = `<span class="contact-display">📞 ${formatPhone(phone)}</span>`;
        }
        else if (!iApproved && grantedByMe.length === 0) {
            if ((phase === "female_approval" && gender === "F") || (phase === "male_approval" && gender === "M")){
                buttonHTML = `<button class="btn btn-sm btn-outline-primary approve-btn">승인</button>`;
            }
            else{
                buttonHTML = `<button class="btn btn-sm btn-outline-primary approve-btn" disabled>승인</button>`;
            }
        } 
        else if (iApproved && phase !== "final") {
            buttonHTML = `<button class="btn btn-sm btn-outline-secondary" disabled>승인 완료</button>`;
        }            

        if(iApproved && (phase === "female_approval" && gender === "F" || phase === "male_approval" && gender === "M" ))
        {
            cancelButtonHTML = `<button class="btn btn-sm btn-outline-primary cancel-btn">승인 취소</button>`;
        }

        li.innerHTML = `
            <div class="flex-grow-1">
                ${choice.name} (또래: ${choice.age}, 마을: ${choice.org})    
                ${contactHTML}
                ${buttonHTML} ${cancelButtonHTML}
            </div>
        `;

        list.appendChild(li);
        bAppend = true;
    }
    if(!bAppend){
        list.innerHTML = '매칭된 결과가 없습니다.';
    }


    // 승인 버튼 클릭 시
    list.addEventListener('click', async e => {
        if (!e.target.classList.contains('approve-btn')) return;
        const li = e.target.closest('li');
        const nameText = li.innerText.split(")")[0].trim()+")"; // 이름 (또래, 마을)
        const confirmMsg = `${nameText} 님을 승인하시겠습니까?`;
        if (!confirm(confirmMsg)) {
            return;
        }

        const candidateId = li.dataset.anon;
        const pubkeyPem = li.dataset.pubkey;
        // console.log("상대방 anon_id: ", candidateId);
        // console.log("상대방 pubkey: ", pubkeyPem);

        // API 호출
        try {
            /* 내 연락처 받기 */

            // console.log("encrypted_phone length:", mydata.encrypted_phone.length);
            // console.log("decoded length:", atob(mydata.encrypted_phone).length);

            const phone = await aesDecrypt(mydata.encrypted_phone, key);

            // let phone;
            // try {
            //     phone = await rsaDecrypt(privateKey, mydata.encrypted_phone);
            // } catch(err) {
            //     console.log('복호화 실패')
            //     return
            // }
            // console.log('복호화된 번호:', phone);

            // 내 연락처 상대 공개키로 암호화
            const rsaPubKey = await importRsaPublicKey(pubkeyPem);
            const grantEnc_phone = await rsaEncrypt(rsaPubKey, phone);
            // console.log('my phone: ', grantEnc_phone);

            const res = await fetch(matching_grant_contact_api, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ to_user: candidateId, reencrypted_phone: grantEnc_phone })
        });

        if (res.ok) {
            // 승인 성공 → 화면 새로고침
            location.reload();
        } else {
            alert("승인에 실패했습니다.");
        }

        } catch (err) {
            console.error("연락처 요청/복호화 실패", err);
            alert("연락처를 가져오는 데 실패했습니다.");
        }
    });


    // 승인 취소 버튼 클릭 시
    list.addEventListener('click', async e => {
        if (!e.target.classList.contains('cancel-btn')) return;
        const li = e.target.closest('li');
        const nameText = li.innerText.split(")")[0].trim()+")"; // 이름 (또래, 마을)
        const confirmMsg = `${nameText} 님의 승인을 취소하시겠습니까?`;
        if (!confirm(confirmMsg)) {
            return;
        }

        const candidateId = li.dataset.anon;
        // console.log("상대방 anon_id: ", candidateId);

        // API 호출
        try {
            const res = await fetch(matching_cancel_grant_api, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ to_user: candidateId })
        });

        if (res.ok) {
            // 승인 성공 → 화면 새로고침
            location.reload();
        } else {
            alert("승인 취소에 실패했습니다.");
        }

        } catch (err) {
            console.error("처리 실패", err);
            // alert("연락처를 가져오는 데 실패했습니다.");
        }
    });

}

