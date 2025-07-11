import json, os
from datetime import datetime
import pytz
from django.http import HttpResponseForbidden
import markdown
from django.utils.safestring import mark_safe
from django.conf import settings

# 1) 설정 파일 로드
_conf = None
def _load_conf():
    global _conf
    if _conf is None:
        path = os.path.join(settings.BASE_DIR, "static", "data",'phases.json')
        with open(path, encoding='utf-8') as f:
            _conf = json.load(f)
    return _conf

# 2) 현재 phase 판별 (KST)
def get_current_phase():
    # print(settings.DEBUG)
    if(settings.DEBUG is True):
        # print("DEBUG")
        return settings.DEBUG_PHASE
    else:
        # print("REAL")
        now = datetime.now(pytz.timezone('Asia/Seoul'))
        conf = _load_conf()
        for phase, period in conf.items():
            start = datetime.fromisoformat(period['start'])
            end   = datetime.fromisoformat(period['end'])
            if start <= now <= end:
                return phase
    return None

# 3) 접근 제어 데코레이터
def phase_access_control(view_func):
    from functools import wraps
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        phase = get_current_phase()
        gender = getattr(request.user, 'gender', None)
        method = request.method
        
        # POST(수정) 허용/차단 로직
        block = False
        if method == 'POST':
            # 표를 그대로 코드로 옮기면:
            if phase == 'signup':
                block = False
            elif phase == 'female_approval':
                # 여성만 결과 수정 허용, 나머지 POST 모두 차단
                if view_func.__name__ == 'grant_contact_api':
                    block = (gender != 'F')
                else:
                    block = True
            elif phase == 'male_approval':
                if view_func.__name__ in ('grant_contact_api', 'results_api'):
                    block = (gender != 'M')
                else:
                    block = True
            else:  # final
                block = True
        
        if block:
            return HttpResponseForbidden("현재 이 작업은 허용되지 않습니다.")
        return view_func(request, *args, **kwargs)
    return _wrapped

# 4) phase 한글 변환
def print_phase(phase):
    if phase == 'signup':
        return '회원 가입'
    elif phase == 'female_approval':
        return '자매 승인'
    elif phase == 'male_approval':
        return '형제 승인'
    elif phase == 'final':
        return '결과 공개'
    else:
        return '오류'


def mark_func(value):
    extensions = ["nl2br", "fenced_code"]
    return mark_safe(markdown.markdown(value, extensions=extensions))