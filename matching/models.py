from django.conf import settings
from django.db import models
from django.contrib.auth.models import (AbstractBaseUser, PermissionsMixin, BaseUserManager)

class Profile(models.Model):
    """
    사용자 프로필: 이름·나이·소속 등을 보관
    (실제 프로젝트에선 User 모델과 OneToOne 관계 맺어 쓸 수 있어요)
    """
    name       = models.CharField(max_length=50)
    age        = models.PositiveSmallIntegerField()
    affiliation= models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.age})"


class Preference(models.Model):
    """
    ‘누가 누구를 선택했는지’ 저장
    from_user는 Django User, to_profile은 Profile
    """
    from_user  = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE)
    to_profile = models.ForeignKey(Profile,
                                   on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user','to_profile')


class UserManager(BaseUserManager):
    def create_user(self, anon_id, password=None, gender=None,
                    public_key=None, encrypted_name=None,
                    encrypted_age=None, encrypted_org=None,
                    encrypted_phone=None):
        if not anon_id:
            raise ValueError("anon_id는 필수입니다")
        user = self.model(
            anon_id=anon_id,
            gender=gender,
            public_key=public_key,
            encrypted_name=encrypted_name,
            encrypted_age=encrypted_age,
            encrypted_org=encrypted_org,
            encrypted_phone=encrypted_phone
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, anon_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(anon_id, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    # 익명 토큰만 유일키로 사용
    anon_id         = models.CharField(max_length=64, unique=True)

    # 필수 개인정보는 모두 암호화된 텍스트로 보관
    gender          = models.CharField(max_length=1, choices=[('M','남'),('F','여')])
    public_key      = models.TextField()  # 클라이언트 공개키 (PEM/base64)
    encrypted_name  = models.TextField()  # capsule+ciphertext
    encrypted_age   = models.TextField()
    encrypted_org   = models.TextField()
    encrypted_phone = models.TextField()

    USERNAME_FIELD = 'anon_id'
    REQUIRED_FIELDS = []

    SERVER_SECRET_B64 = settings.SERVER_SECRET_B64

    objects = UserManager()

class Selection(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_selections')
    tag       = models.CharField(max_length=64)  # HMAC(server_secret, 대상 anon_id)

class ReEncKey(models.Model):
    # B→A 재암호화 키
    from_user    = models.ForeignKey(User, related_name='reenc_from', on_delete=models.CASCADE)
    to_user      = models.ForeignKey(User, related_name='reenc_to',   on_delete=models.CASCADE)
    key_material = models.TextField()  # base64 인코딩된 re‑enc key