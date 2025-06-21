import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django_htmx.http import HttpResponseClientRedirect
from django.http import JsonResponse, HttpResponseBadRequest
from .models import User

def index(request):
    return render(request, 'index.html')

@login_required(login_url='common:login')
def select_page(request):
    # 사용자가 선택 폼을 보는 페이지
    user = request.user
    return render(request, 'matching/select.html', {
        'server_secret_b64': User.SERVER_SECRET_B64,
        'user_salt': user.salt,
        'anon_id': user.anon_id,
    })

@login_required(login_url='common:login')
def select_api(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST만 허용")

    data = json.loads(request.body)
    encrypted = data.get('encrypted_choices')
    if encrypted is None:
        return HttpResponseBadRequest("선택 데이터 누락")
    # AES‑GCM 암호문을 User.encrypted_choices에 저장
    user = request.user
    user.encrypted_choices = encrypted
    user.save()
    return JsonResponse({'status':'ok'})

@login_required(login_url='common:login')
def choices_api(request):
    # 로그인된 사용자의 저장된 암호문을 반환
    return JsonResponse({'encrypted_choices': request.user.encrypted_choices})

@login_required(login_url='common:login')
def results_page(request):
    # 사용자가 선택 폼을 보는 페이지
    user = request.user
    return render(request, 'matching/results.html', {
        'server_secret_b64': User.SERVER_SECRET_B64,
        'user_salt': user.salt,
    })

@login_required(login_url='common:login')
def results_api(request):
    # 오직 여성 사용자만 접근 (예: gender == 'F')
    if request.user.gender != 'F':
        return JsonResponse({'error': '접근 불가'}, status=403)

    # 예시: 여성 사용자가 내 선택(HMAC 태그)과 다른 사용자의 선택 태그를 비교하여 서로 일치하는 후보를 "상호 매칭"으로 간주합니다.
    # 이 예시는 실제 암호화 자료를 활용하는 대신, 간단한 방식으로 설명합니다.
    # 실제로는 양쪽 사용자가 같은 공개 프로필 정보를 기반으로 동일한 HMAC 태그를 계산했어야 합니다.
    
    # 내 profile_tag
    my_tag = request.user.profile_tag

    # 나를 선택한 사람들
    # selections = Selection.objects.filter(tag=my_tag).exclude(from_user=request.user)
    # candidate_ids = selections.values_list('from_user__id', flat=True).distinct()
    # matched = User.objects.filter(id__in=candidate_ids)
    
    # 각 후보에 대해, 공개 프로필 정보(암호화된 상태)를 리스트로 구성합니다.
    results = []
    # for candidate in matched:
    #     # print(candidate.profile_tag)
    #     results.append({
    #         'candidate_id': candidate.anon_id,  # 암호화된 ID도 물론 단순 태그 형태로 제공 (여기서는 예시)
    #         'encrypted_name': candidate.encrypted_name,
    #         'encrypted_age': candidate.encrypted_age,
    #         'encrypted_org': candidate.encrypted_org,
    #         'profile_tag' : candidate.profile_tag,
    #         # 후보 연락처 암호문은 별도로 제공되지 않음; 사용자 요청 시 공개 (아래 재암호화 프로세스 사용)
    #     })

    return JsonResponse({'matches': results})

@login_required(login_url='common:login')
def get_contact_api(request):
    # 반드시 여자 사용자 요청만 처리
    if request.user.gender != 'F':
        return JsonResponse({'error': '접근 불가'}, status=403)
    candidate_id = request.GET.get('candidate_id')
    if not candidate_id:
        return JsonResponse({'error': '후보 정보 누락'}, status=400)
    try:
        candidate = User.objects.get(anon_id=candidate_id)
    except User.DoesNotExist:
        return JsonResponse({'error': '후보 없음'}, status=404)
    
    # 여기에 프록시 리암호화 로직 적용.
    # 예를 들어, 후보가 자신의 연락처를 R_enc(key_material)을 통해 재암호화한 결과가 있다면,
    # 그 자료를 그대로 반환하여 클라이언트에서 여성 사용자의 암호화 키로 복호화하게 합니다.
    # 아래는 간단한 예시로, candidate.encrypted_phone 를 그대로 반환하는 구조입니다.
    # 실제 구현에서는 절대로 평문으로 복호화하지 않습니다.
    return JsonResponse({
        'encrypted_phone': candidate.encrypted_phone
        # 재암호화된 데이터가 여기 포함되어야 함
    })