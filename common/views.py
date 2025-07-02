import json
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
import os, base64
from django.contrib.auth.decorators import login_required
# from common.forms import UserForm
from matching.models import User
from common.utils import get_current_phase, phase_access_control
from django.urls import reverse

def logout_view(request):
    logout(request)
    return redirect('index')

def login_page(request):
    if request.method == 'POST':
        anon_id  = request.POST.get('anon_id')
        password = request.POST.get('password')

        if not all([anon_id, password]):
            return JsonResponse({'status': 'error', 'message': '아이디 또는 비밀번호 누락'}, status=400)
        
        user = authenticate(request, username=anon_id, password=password)
        if user:
            login(request, user)
            return JsonResponse({'status':'ok', 'redirect': '/', 'user_salt': user.salt})
        return JsonResponse({'status':'error','message':'아이디/비밀번호 불일치'}, status=401)
    context = {
        'server_secret_b64': User.SERVER_SECRET_B64,  # settings에서 base64로 제공
    }
    return render(request, 'common/login.html', context)
    
@csrf_exempt # fetch 사용 시 필요 (단, 보안을 위해 CSRF 토큰은 JS에서 함께 전달)
def signup(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "잘못된 JSON"}, status=400)
        
        required_fields = [
            "anon_id", "password", "gender", "public_key", "encrypted_privkey",
            "encrypted_name", "encrypted_age", "encrypted_org",
            "encrypted_phone", "profile_tag", "salt"
        ]
        if not all(data.get(f) for f in required_fields):
            return JsonResponse({"status": "error", "message": "필수 항목 누락"}, status=400)

        anon_id = data['anon_id']
        password = data['password']
        gender = data['gender']
        public_key = data['public_key']
        encrypted_privkey = data['encrypted_privkey']
        encrypted_name = data['encrypted_name']
        encrypted_age = data['encrypted_age']
        encrypted_org = data['encrypted_org']
        encrypted_phone = data['encrypted_phone']
        profile_tag = data['profile_tag']
        salt = data['salt']

        User.objects.create_user(
            anon_id=anon_id,
            password=password,
            gender=gender,
            public_key=public_key,
            encrypted_privkey = encrypted_privkey,
            encrypted_name=encrypted_name,
            encrypted_age=encrypted_age,
            encrypted_org=encrypted_org,
            encrypted_phone=encrypted_phone,
            profile_tag=profile_tag,
            salt=salt,
        )

        # username = form.cleaned_data.get('username')
        # raw_password = form.cleaned_data.get('password1')
        # user = authenticate(username=username, password=raw_password) # 사용자 인증
        # login(request, user) # 로그인
        return JsonResponse({"status": "ok"})
    
    # Get 요청시
    user_salt = base64.b64encode(os.urandom(16)).decode()
    context = {
        'server_secret_b64': User.SERVER_SECRET_B64,  # settings에서 base64로 제공
        'user_salt': user_salt,
    }
    return render(request, 'common/signup.html', context)


@login_required(login_url='/common/login')
def get_myinfo_api(request):
    # 로그인된 사용자의 저장된 암호문을 반환
    return JsonResponse({'encrypted_name': request.user.encrypted_name,
                        'encrypted_age': request.user.encrypted_age,
                        'encrypted_org': request.user.encrypted_org,
                        'encrypted_phone': request.user.encrypted_phone,
                        'encrypted_privkey': request.user.encrypted_privkey,
                        'gender': request.user.gender,})

@login_required(login_url='/common/login')
@phase_access_control
def update_myinfo_api(request):
    # 정보 업데이트
    if request.method != "POST":
        return JsonResponse({"error": "POST 요청만 허용"}, status=405)
    
    user = request.user
    data = json.loads(request.body)
    current_password = data.get("password")
    # current_password = request.POST.get("password")
    # new_password = request.POST.get("password21","")
    # print(new_password)
    if not user.is_authenticated:
        return JsonResponse({'message': '로그인이 필요합니다.'}, status=403)
    
    if not user.check_password(current_password):
        return JsonResponse({"status": "error", "message": "현재 비밀번호가 일치하지 않습니다."}, status=403)

    
    try:
        request.user.encrypted_name = data.get("encrypted_name", "")
        request.user.encrypted_age = data.get("encrypted_age", "")
        request.user.encrypted_org = data.get("encrypted_org", "")
        request.user.encrypted_phone = data.get("encrypted_phone", "")
        request.user.encrypted_privkey = data.get("encrypted_privkey", "")
        request.user.profile_tag = data.get("profile_tag", "")
        new_password = data.get("password21", "")
        if new_password and new_password.strip():  # 공백 포함 비어있는 문자열도 제외
            request.user.set_password(new_password)
            user.save(update_fields=[
                "encrypted_name", "encrypted_age", "encrypted_org",
                "encrypted_phone", "profile_tag", "password", "encrypted_privkey"
            ])
            update_session_auth_hash(request, user)
        else:
            user.save(update_fields=[
                "encrypted_name", "encrypted_age", "encrypted_org",
                "encrypted_phone", "profile_tag"
            ])
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required(login_url='/common/login')
def myinfo_page(request):
    #내 정보 확인
    user = request.user
    phase = get_current_phase()

    return render(request, 'common/info.html', {
        'server_secret_b64': User.SERVER_SECRET_B64,
        'user_salt': user.salt,
        'anon_id': user.anon_id,
        'current_phase': phase,
    })