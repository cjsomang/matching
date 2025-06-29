import json
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
import os, base64
from django.contrib.auth.decorators import login_required
# from common.forms import UserForm
from matching.models import User

def logout_view(request):
    logout(request)
    return redirect('index')

def login_page(request):
    if request.method == 'POST':
        anon_id  = request.POST.get('anon_id')
        password = request.POST.get('password')

        if not all([anon_id, password]):
            return HttpResponseBadRequest("필수 필드 누락")
        
        user = authenticate(request, username=anon_id, password=password)
        if user:
            login(request, user)
            # redirect_url = request.POST.get('next') or 'index'
            # return JsonResponse({'status':'ok', 'redirect':redirect_url})
            return JsonResponse({'status':'ok', 'redirect': '/', 'user_salt': user.salt})
        return JsonResponse({'status':'error','message':'아이디/비밀번호 불일치'}, status=401)
        # return HttpResponse("아이디/비밀번호 불일치")
    context = {
        'server_secret_b64': User.SERVER_SECRET_B64,  # settings에서 base64로 제공
        'next': request.GET.get('next', '/'),
    }
    return render(request, 'common/login.html', context)
    

def signup(request):
    if request.method == "POST":
        anon_id = request.POST.get('anon_id')
        password = request.POST.get('password')
        gender = request.POST.get('gender')
        public_key = request.POST.get('public_key')
        encrypted_privkey = request.POST.get('encrypted_privkey')
        encrypted_name = request.POST.get('encrypted_name')
        encrypted_age = request.POST.get('encrypted_age')
        encrypted_org = request.POST.get('encrypted_org')
        encrypted_phone = request.POST.get('encrypted_phone')
        profile_tag = request.POST.get('profile_tag')
        salt = request.POST.get('salt')

        if not all([anon_id, password, gender, public_key, encrypted_privkey,
            encrypted_name, encrypted_age, encrypted_org, encrypted_phone, profile_tag, salt]):
            # print(password)
            # print(gender)
            # print(public_key)
            # print(encrypted_name)
            # print(encrypted_age)
            # print(encrypted_org)
            # print(encrypted_phone)
            # print(profile_tag)
            return HttpResponseBadRequest("필수 필드 누락")
        
        # data = json.loads(request.body)
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
        return HttpResponse("<p>회원가입이 완료되었습니다.</p>")
    # else:
        # form = UserForm()
    # return render(request, 'common/signup.html', {'form': form})
    user_salt = base64.b64encode(os.urandom(16)).decode()
    context = {
        'server_secret_b64': User.SERVER_SECRET_B64,  # settings에서 base64로 제공
        'user_salt': user_salt,
    }
    return render(request, 'common/signup.html', context)


@login_required(login_url='common:login')
def get_myinfo_api(request):
    # 로그인된 사용자의 저장된 암호문을 반환
    return JsonResponse({'encrypted_name': request.user.encrypted_name,
                        'encrypted_age': request.user.encrypted_age,
                        'encrypted_org': request.user.encrypted_org,
                        'encrypted_phone': request.user.encrypted_phone,
                        'encrypted_privkey': request.user.encrypted_privkey})

@login_required(login_url='common:login')
def update_myinfo_api(request):
    # 정보 업데이트
    if request.method != "POST":
        return JsonResponse({"error": "POST 요청만 허용"}, status=405)

    data = json.loads(request.body)
    try:
        request.user.encrypted_name = data.get("encrypted_name", "")
        request.user.encrypted_age = data.get("encrypted_age", "")
        request.user.encrypted_org = data.get("encrypted_org", "")
        request.user.encrypted_phone = data.get("encrypted_phone", "")
        request.user.profile_tag = data.get("profile_tag", "")
        request.user.save(update_fields=["encrypted_name", "encrypted_age", "encrypted_org", "encrypted_phone", "profile_tag"])
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required(login_url='common:login')
def myinfo_page(request):
    #내 정보 확인
    user = request.user
    return render(request, 'common/info.html', {
        'server_secret_b64': User.SERVER_SECRET_B64,
        'user_salt': user.salt,
        'anon_id': user.anon_id,
    })