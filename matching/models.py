from django.conf import settings
from django.db import models
from django.contrib.auth.models import (AbstractBaseUser, PermissionsMixin, BaseUserManager)



class UserManager(BaseUserManager):
    def create_user(self, anon_id, password=None, gender=None,
                    public_key=None, encrypted_privkey=None, encrypted_name=None,
                    encrypted_age=None, encrypted_org=None,
                    encrypted_phone=None, profile_tag=None, encrypted_choices=None, salt=None):
        if not anon_id:
            raise ValueError("anon_id는 필수입니다")
        # extra_fields.setdefault('salt', base64.b64encode(os.urandom(16)).decode())
        user = self.model(
            anon_id=anon_id,
            gender=gender,
            public_key=public_key,
            encrypted_privkey=encrypted_privkey,
            encrypted_name=encrypted_name,
            encrypted_age=encrypted_age,
            encrypted_org=encrypted_org,
            encrypted_phone=encrypted_phone,
            profile_tag=profile_tag,
            salt=salt,
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
    salt            = models.CharField(max_length=64, blank=True)  # Base64 인코딩된 salt를 저장
    # 필수 개인정보는 모두 암호화된 텍스트로 보관
    gender          = models.CharField(max_length=1, choices=[('M','남'),('F','여')])
    public_key      = models.TextField()  # Umbral 공개키 (전화번호 암호화/복호화용)
    encrypted_privkey = models.TextField()
    encrypted_name  = models.TextField()  # capsule+ciphertext
    encrypted_age   = models.TextField()
    encrypted_org   = models.TextField()
    encrypted_phone = models.TextField()    
    profile_tag    = models.CharField(max_length=64, unique=True)
    encrypted_choices = models.TextField(blank=True, null=True)

    USERNAME_FIELD = 'anon_id'
    REQUIRED_FIELDS = []

    SERVER_SECRET_B64 = settings.SERVER_SECRET_B64

    objects = UserManager()

class Selection(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_selections')
    tag       = models.CharField(max_length=88)  # HMAC(server_secret, JSON(name,age,org))


class ContactGrant(models.Model):
    from_user = models.ForeignKey(User, related_name="granted_contacts", on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name="received_contacts", on_delete=models.CASCADE)
    reencrypted_phone = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')