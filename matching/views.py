import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django_htmx.http import HttpResponseClientRedirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from .models import User, Selection, ContactGrant
from common.utils import get_current_phase, phase_access_control, print_phase
import os
import markdown
# from django import template
# from django.utils.safestring import mark_safe
from common.utils import mark_func

def index(request):
    file_path = os.path.join(os.path.dirname(__file__), '..','static', 'notice.md')  # 위치는 자유롭게
    with open(file_path, encoding='utf-8') as f:
        md_content = f.read()
    html_content = mark_func(md_content)
    phase = get_current_phase()
    # print_phase(phase)

    return render(request, 'index.html', {'text': html_content, 'phase': print_phase(phase)})

@login_required
def select_page(request):
    # 사용자가 선택 폼을 보는 페이지
    user = request.user
    phase = get_current_phase()
    return render(request, 'matching/select.html', {
        'server_secret_b64': User.SERVER_SECRET_B64,
        'user_salt': user.salt,
        'anon_id': user.anon_id,
        'current_phase': phase,
    })

@login_required
@phase_access_control
def select_api(request):
    if request.method != 'POST':
        return JsonResponse({'message':'POST만 허용'}, status=405)

    data = json.loads(request.body)
    encrypted = data.get('encrypted_choices')
    tags = data.get('tags', [])

    if not tags or not encrypted:
        return JsonResponse({'message':'선택 데이터 누락'}, status=400)
    elif (not (1 <= len(tags) <= 3)):
        return JsonResponse({'message':'1~3명 선택 가능'}, status=400)

    # AES‑GCM 암호문을 User.encrypted_choices에 저장
    # user = request.user
    # user.encrypted_choices = encrypted
    # user.save()

    # # 1) Selection 테이블 갱신
    # Selection.objects.filter(from_user=request.user).delete()
    # for tag in tags:
    #     Selection.objects.create(from_user=request.user, tag=tag)

    # # 2) 전체 choices AES‑GCM 암호문도 저장(선택 기록 복호화용)
    # if encrypted is not None:
    #     request.user.encrypted_choices = encrypted
    #     request.user.save(update_fields=['encrypted_choices'])
    try:
        # 1) Selection 테이블 갱신
        Selection.objects.filter(from_user=request.user).delete()
        for tag in tags:
            Selection.objects.create(from_user=request.user, tag=tag)

        # 2) encrypted_choices 저장
        request.user.encrypted_choices = encrypted
        request.user.save(update_fields=['encrypted_choices'])

    except Exception as e:
        # 내부 오류일 때는 500과 함께 메시지를 남깁니다
        return JsonResponse({'message': str(e)}, status=500)

    return JsonResponse({'status':'ok'})

@login_required
def choices_api(request):
    # 로그인된 사용자의 저장된 선택지 암호문을 반환
    return JsonResponse({'encrypted_choices': request.user.encrypted_choices})

@login_required
def results_page(request):
    # 사용자가 선택 폼을 보는 페이지
    user = request.user
    phase = get_current_phase()
    gender = user.gender
    if phase == "signup" or (phase == "female_approval" and gender == "M"):
        return render(request, 'matching/block.html', {
            'server_secret_b64': User.SERVER_SECRET_B64,
            'user_salt': user.salt,
            'anon_id': user.anon_id,
            'current_phase': phase,
            'gender': gender,
        })
    return render(request, 'matching/results.html', {
        'server_secret_b64': User.SERVER_SECRET_B64,
        'user_salt': user.salt,
        'anon_id': user.anon_id,
        'current_phase': phase,
        'gender': gender,
    })

@login_required
def results_api(request):
    # 오직 여성 사용자만 접근 (예: gender == 'F')
    if request.user.gender != 'F': # 남자 사용자
        # 남자 사용자는 여성 사용자가 grant 한 경우에만 접근 가능
        my_tag = request.user.profile_tag

        # 나를 선택한 사람들
        selections = Selection.objects.filter(tag=my_tag).exclude(from_user=request.user)
        candidate_ids = selections.values_list('from_user__id', flat=True).distinct()
        matched = User.objects.filter(id__in=candidate_ids)

        granted_ids = ContactGrant.objects.filter(to_user=request.user)\
                            .values_list('from_user__anon_id', flat=True)
        
        # 각 후보에 대해, 공개 프로필 정보(암호화된 상태)를 리스트로 구성합니다.
        results = []
        for candidate in matched:
            # print(candidate.profile_tag)
            if candidate.anon_id in granted_ids:
                results.append({
                    'candidate_id': candidate.anon_id,  # 암호화된 ID도 물론 단순 태그 형태로 제공 (여기서는 예시)
                    'profile_tag' : candidate.profile_tag,
                    'public_key': candidate.public_key,
                    # 후보 연락처 암호문은 별도로 제공되지 않음; 사용자 요청 시 공개 (아래 재암호화 프로세스 사용)
                })
        
        return JsonResponse({'matches': results})

    # 예시: 여성 사용자가 내 선택(HMAC 태그)과 다른 사용자의 선택 태그를 비교하여 서로 일치하는 후보를 "상호 매칭"으로 간주합니다.
    # 이 예시는 실제 암호화 자료를 활용하는 대신, 간단한 방식으로 설명합니다.
    # 실제로는 양쪽 사용자가 같은 공개 프로필 정보를 기반으로 동일한 HMAC 태그를 계산했어야 합니다.
    #### 여자 사용자

    # 내 profile_tag
    my_tag = request.user.profile_tag

    # 나를 선택한 사람들
    selections = Selection.objects.filter(tag=my_tag).exclude(from_user=request.user)
    candidate_ids = selections.values_list('from_user__id', flat=True).distinct()
    matched = User.objects.filter(id__in=candidate_ids)
    
    # 각 후보에 대해, 공개 프로필 정보(암호화된 상태)를 리스트로 구성합니다.
    results = []
    for candidate in matched:
        # print(candidate.profile_tag)
        results.append({
            'candidate_id': candidate.anon_id,  # 암호화된 ID도 물론 단순 태그 형태로 제공 (여기서는 예시)
            # 'encrypted_name': candidate.encrypted_name,
            # 'encrypted_age': candidate.encrypted_age,
            # 'encrypted_org': candidate.encrypted_org,
            'profile_tag' : candidate.profile_tag,
            'public_key': candidate.public_key,
        })

    return JsonResponse({'matches': results})

@login_required
def grant_contact_api(request): # 승인 API
    if request.method != 'POST':
        return HttpResponseBadRequest("POST만 허용")

    data = json.loads(request.body)
    to_user_id = data.get('to_user')
    reenc_phone = data.get('reencrypted_phone')

    if not to_user_id or not reenc_phone:
        return JsonResponse({'error': '필수 데이터 누락'}, status=400)

    try:
        to_user = User.objects.get(anon_id=to_user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': '대상 없음'}, status=404)

    # 중복 방지
    ContactGrant.objects.update_or_create(
        from_user=request.user, to_user=to_user,
        defaults={'reencrypted_phone': reenc_phone}
    )
    return JsonResponse({'status': 'ok'})

@login_required
def get_granted_contact_api(request):
    # 나를 승인한 상대 리스트
    from_user_id = request.GET.get('from_user')

    # 1) 특정 사용자로부터 받은 연락처만 요청한 경우
    if from_user_id:
        try:
            from_user = User.objects.get(anon_id=from_user_id)
            grant = ContactGrant.objects.get(from_user=from_user, to_user=request.user)
            return JsonResponse({
                'from_user': from_user.anon_id,
                'reencrypted_phone': grant.reencrypted_phone
            })
        except (User.DoesNotExist, ContactGrant.DoesNotExist):
            return JsonResponse({'from_user': None, 'reencrypted_phone': None})

    # 2) 전체 연락처 요청 (내가 받은 모든 연락처)
    all_grants = ContactGrant.objects.filter(to_user=request.user)
    result = {
        'granted': [
            {
                'from_user': g.from_user.anon_id,
                'reencrypted_phone': g.reencrypted_phone
            }
            for g in all_grants
        ]
    }
    return JsonResponse(result)

@login_required
def get_granted_by_me_api(request):
    # 내가 승인한 상대 리스트
    # from_user_id = request.user

    # 1) 내가 승인한 특정 사용자만 요청한 경우
    # if from_user_id:
    #     try:
    #         from_user = User.objects.get(anon_id=from_user_id)
    #         grant = ContactGrant.objects.get(from_user=from_user, to_user=request.user)
    #         return JsonResponse({
    #             'from_user': from_user.anon_id,
    #             'reencrypted_phone': grant.reencrypted_phone
    #         })
    #     except (User.DoesNotExist, ContactGrant.DoesNotExist):
    #         return JsonResponse({'from_user': None, 'reencrypted_phone': None})

    # 2) 전체 연락처 요청 (내가 승인한 모든 연락처)
    all_grants = ContactGrant.objects.filter(from_user=request.user)
    result = {
        'granted': [
            {
                'to_user': g.to_user.anon_id
                # 'reencrypted_phone': g.reencrypted_phone
            }
            for g in all_grants
        ]
    }
    return JsonResponse(result)

@login_required
def cancel_grant_api(request): # 승인 취소 API
    if request.method != 'POST':
        return HttpResponseBadRequest("POST만 허용")
    
    try:
        deleted_count, _ = ContactGrant.objects.filter(from_user_id=request.user).delete()
        if deleted_count == 0:
            return JsonResponse({'error': '승인 내역이 없습니다.'}, status=404)
        return JsonResponse({'status': 'ok'})

    except Exception as e:
        return JsonResponse({'error': f'처리 중 오류 발생: {str(e)}'}, status=500)
