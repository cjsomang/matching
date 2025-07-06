export async function loadAndRenderPhases(targetId = "phase-list") {
    const res = await fetch("/static/data/phases.json");
    const data = await res.json();

    const formatter = new Intl.DateTimeFormat("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        weekday: "short",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
        timeZone: "Asia/Seoul"
    });

    const phaseNames = {
        signup: "회원 가입 기간",
        female_approval: "자매 승인 기간",
        male_approval: "형제 승인 기간",
        final: "결과 공개 기간"
    };

    const ul = document.getElementById(targetId);
    ul.innerHTML = "";

    for (const [phase, period] of Object.entries(data)) {
        const start = formatter.format(new Date(period.start));
        const end = formatter.format(new Date(period.end));
        const li = document.createElement("li");
        li.textContent = `${phaseNames[phase]}: ${start} ~ ${end}`;
        ul.appendChild(li);
    }
}
