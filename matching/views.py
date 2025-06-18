import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django_htmx.http import HttpResponseClientRedirect
from django.http import JsonResponse, HttpResponseBadRequest
from .models import Selection, User

def index(request):
    return render(request, 'index.html')

@login_required(login_url='common:login')
def select_page(request):
    # 사용자가 선택 폼을 보는 페이지
    return render(request, 'matching/select.html', {
        'server_secret_b64': User.SERVER_SECRET_B64
    })

@csrf_exempt
def select_api(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("POST만 허용")

    data = json.loads(request.body)
    tags = data.get('tags', [])
    if not (1 <= len(tags) <= 3):
        return HttpResponseBadRequest("1~3명 선택 가능")

    # 기존 선택 삭제 후 새로 저장
    Selection.objects.filter(from_user=request.user).delete()
    for tag in tags:
        Selection.objects.create(from_user=request.user, tag=tag)

    return JsonResponse({'status':'ok'})
# @login_required(login_url='common:login')
# def viewlist(request):
#     # 본인을 제외한 모든 프로필
#     profiles = Profile.objects.exclude(
#         # User와 Profile이 일대일 매핑이라고 가정할 때
#         name=request.user.username  
#     )
#     # 내가 선택한 프로필 ID 목록
#     selected = Preference.objects.filter(
#         from_user=request.user
#     ).values_list('to_profile_id', flat=True)

#     return render(request, 'matching/viewlist.html', {
#         'profiles': profiles,
#         'selected': selected,
#     })


# @login_required(login_url='common:login')
# def select_profile(request, pk):
#     """
#     HTMX로 호출되는 선택 토글 뷰.
#     이미 선택한 상대면 취소, 아니면 생성.
#     partial HTML(선택된 목록) 리턴
#     """
#     profile = get_object_or_404(Profile, pk=pk)
#     pref, created = Preference.objects.get_or_create(
#         from_user=request.user, to_profile=profile
#     )
#     if not created:
#         pref.delete()

#     # HTMX 요청이면 선택 현황만 부분 렌더
#     if request.htmx:
#         selected = Preference.objects.filter(
#             from_user=request.user
#         ).select_related('to_profile')
#         return render(request,
#                       'matching/_selection_list.html',
#                       {'selected': selected})

#     # 일반 요청 시엔 인덱스로 리다이렉트
#     return HttpResponseClientRedirect(request.path_info.replace(
#         f'select/{pk}/', ''
#     ))
