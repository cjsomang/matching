from django.contrib import admin
from django.db.models import Count, Q
from django.template.response import TemplateResponse
from collections import Counter
from .models import Stats, User, Selection, ContactGrant

@admin.register(Stats)
class StatsAdmin(admin.ModelAdmin):
    # 레코드 리스트(=대시보드) 화면 템플릿
    change_list_template = "admin/stats_change_list.html"

    def changelist_view(self, request, extra_context=None):
        # 1) 남/녀 회원수
        total_male   = User.objects.filter(gender='M').count()
        total_female = User.objects.filter(gender='F').count()

        # 2) 상호 매칭된 후보 수
        # 2-1) 모든 선택 기록(from_user_id, tag) 가져오기
        selections = Selection.objects.values_list('from_user_id', 'tag')
        
        # 2-2) profile_tag → user_id 매핑 미리 생성
        tag_to_user = {
            user.profile_tag: user.id
            for user in User.objects.all()
        }

        mutual_pairs = set()

        for from_user_id, tag in selections:
            # 2-3) tag로 to_user_id 찾기 (없으면 skip)
            to_id = tag_to_user.get(tag)
            if to_id is None:
                continue

            # 2-4) from_user 인스턴스 조회 (없으면 skip)
            try:
                user_a = User.objects.get(id=from_user_id)
                from_id = user_a.id
            except User.DoesNotExist:
                continue

            # 2-5) user_a의 profile_tag 
            from_tag = user_a.profile_tag

            # 2-6) B(to_id)가 A를 선택했는지 확인
            exists = Selection.objects.filter(
                from_user_id=to_id,
                tag=from_tag
            ).exists()
            if exists:
                # (A,B)와 (B,A)가 중복되지 않도록 정렬된 튜플로 set에 추가
                pair = tuple(sorted((from_id, to_id)))
                mutual_pairs.add(pair)

        # set에 저장된 고유 쌍의 수를 반환
        mutual_tags = len(mutual_pairs)


        # 3) 최종 매칭 커플 수 (서로 연락처를 주고받은 유일한 pair 수)
        # ContactGrant에서 모든 (from_user, to_user) 쌍을 모아
        # set으로 정렬 후 고유(pair) 개수 계산

        try:
            # 3-1) 모든 grant 레코드(from, to)를 리스트로 가져옴
            grants = ContactGrant.objects.values_list('from_user_id', 'to_user_id')
        except Exception as e:
            # DB 에러 등 예외 발생 시 0 반환
            return 0

        mutual_pairs = set()

        for from_user_id, to_user_id in grants:
            # 2) 역방향 레코드가 있는지 확인
            try:
                exists = ContactGrant.objects.filter(
                    from_user_id=to_user_id,
                    to_user_id=from_user_id
                ).exists()
            except Exception:
                # 쿼리 오류 나면 해당 루프만 스킵
                continue

            if exists:
                # (A,B)와 (B,A)를 중복 없이 세기 위해 작은 값 먼저 튜플화
                pair = tuple(sorted((from_id, to_id)))
                mutual_pairs.add(pair)

        couple_count = len(mutual_pairs)

        extra_context = {
            'total_male':    total_male,
            'total_female':  total_female,
            'mutual_tags':   mutual_tags,
            'couple_count':  couple_count,
        }
        return super().changelist_view(request, extra_context=extra_context)
