from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from core.models import BaseModel
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where phone number is the unique identifier
    for authentication instead of usernames. Email is also required.
    Username will still exist on the model (from AbstractUser) but may not be used for login.
    """
    def create_user(self, phone_number, email, password=None, username=None, **extra_fields):
        """
        Creates and saves a User with the given phone number, email and password.
        """
        if not phone_number:
            raise ValueError(_('The Phone Number must be set'))
        if not email:
            raise ValueError(_('The Email must be set'))

        email = self.normalize_email(email)
        # If username is not provided, generate one (e.g., from phone_number or a default)
        # AbstractUser requires username.
        if not username:
            username = phone_number # Or some other logic to ensure username is present

        user = self.model(phone_number=phone_number, email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, email, password=None, username=None, **extra_fields):
        """
        Creates and saves a superuser with the given phone number, email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True) # Superusers should be active by default

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        # If username is not provided for superuser, generate one
        if not username:
            username = phone_number # Or default like 'admin_' + phone_number

        return self.create_user(phone_number, email, password, username=username, **extra_fields)


class User(AbstractUser):
    # Username can be non-unique if login is via phone/email.
    # If username must be unique for other reasons, remove unique=False or set to True.
    # For this project, let's assume username can be non-unique to allow flexibility.
    # However, Django's AbstractUser username is unique by default.
    # To make it non-unique, we'd need to create a custom manager and possibly more.
    # For now, let's keep username unique as per Django standard and clarify if it NEEDS to be non-unique.
    # If phone is the primary identifier, username might be an internal construct or removed.
    # Let's make email unique for password resets and notifications, if not already.
    email = models.EmailField(unique=True, verbose_name='电子邮箱')
    phone_number = models.CharField(max_length=20, unique=True, verbose_name='手机号码', help_text='用于登录和接收通知')
    signing_company = models.ForeignKey(
        'organizations.SigningCompany',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='关联签约公司',
        help_text='用户所属的签约公司（如果适用）'
    )
    status_choices = [
        (1, '正常'),
        (2, '禁用'),
        (3, '删除'),
    ]
    status = models.SmallIntegerField(choices=status_choices, default=1, verbose_name='用户状态', help_text='例如：1-正常，2-禁用，3-删除')
    contract_details = models.TextField(null=True, blank=True, verbose_name='签约详情', help_text='存储与签约公司的合同相关信息')
    is_verified = models.BooleanField(default=False, verbose_name='是否已实名认证', help_text='标记用户是否已通过实名认证流程')

    # Override 'username' to allow it to be blank if phone_number is the main identifier
    # This is complex with AbstractUser. A simpler approach for now is to ensure username is populated,
    # possibly automatically from phone_number if not provided.
    # For now, we rely on standard AbstractUser behavior where username is required and unique.
    # The CustomUserManager above handles ensuring username is set, even if phone_number is primary.

    # Add related_name to avoid clashes with default User model's fields.
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="custom_user_groups",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="custom_user_permissions",
        related_query_name="user",
    )

    # Remove first_name and last_name if not needed, or make them optional
    first_name = models.CharField(max_length=150, blank=True, verbose_name='名字')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='姓氏')

    USERNAME_FIELD = 'phone_number' # Use phone_number for login
    REQUIRED_FIELDS = ['username', 'email'] # username still required by AbstractUser internally, email for password resets etc.
                                        # phone_number is USERNAME_FIELD.

    objects = CustomUserManager() # Use the custom manager

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        db_table_comment = "用户信息表"

    def __str__(self):
        return self.username


class Role(BaseModel):
    name = models.CharField(max_length=100, unique=True, verbose_name='角色名称')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='角色描述')

    class Meta:
        verbose_name = '角色'
        verbose_name_plural = verbose_name
        db_table_comment = "角色信息表"

class Permission(BaseModel):
    # Using Django's built-in permissions is often preferred.
    # This custom Permission model is if specific needs go beyond ContentType-based permissions.
    name = models.CharField(max_length=100, unique=True, verbose_name='权限名称', help_text='人类可读的权限名，如 "查看订单"')
    codename = models.CharField(max_length=100, unique=True, verbose_name='权限代码', help_text='程序中使用的权限标识，如 "view_order"')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='权限描述')
    # category = models.CharField(max_length=50, null=True, blank=True, verbose_name='权限分类', help_text='例如：用户管理, 订单管理')


    class Meta:
        verbose_name = '权限'
        verbose_name_plural = verbose_name
        db_table_comment = "自定义权限表"

class UserRoleMap(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='用户', help_text='关联的用户')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name='角色', help_text='关联的角色')

    class Meta:
        unique_together = ('user', 'role')
        verbose_name = '用户角色映射'
        verbose_name_plural = verbose_name
        db_table_comment = "用户与角色关系映射表"

class RolePermissionMap(BaseModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name='角色', help_text='关联的角色')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, verbose_name='权限', help_text='关联的自定义权限')

    class Meta:
        unique_together = ('role', 'permission')
        verbose_name = '角色权限映射'
        verbose_name_plural = verbose_name
        db_table_comment = "角色与自定义权限关系映射表"


class Menu(BaseModel):
    name = models.CharField(max_length=100, verbose_name='菜单名称')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name='父级菜单', help_text='此菜单的父级菜单')
    url = models.CharField(max_length=255, null=True, blank=True, verbose_name='菜单URL', help_text='前端路由或链接')
    icon = models.CharField(max_length=100, null=True, blank=True, verbose_name='菜单图标', help_text='例如 Element Plus 图标类名')
    order = models.IntegerField(default=0, verbose_name='显示顺序', help_text='数字越小越靠前')
    is_visible = models.BooleanField(default=True, verbose_name='是否可见', help_text='控制菜单是否在界面上显示')
    # permission_required = models.ForeignKey(Permission, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='访问所需权限', help_text='访问此菜单所需的自定义权限')
    # Use Django's built-in permission system for menu visibility if possible, by associating menus with views that have permission checks.
    # Or, link to a custom Permission codename directly.
    # permission_codename = models.CharField(max_length=100, null=True, blank=True, verbose_name='权限码关联', help_text='关联的权限代码，用于控制显隐')


    class Meta:
        verbose_name = '菜单'
        verbose_name_plural = verbose_name
        ordering = ['order', 'name']
        db_table_comment = "系统菜单配置表"

class RoleMenuMap(BaseModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name='角色', help_text='关联的角色')
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, verbose_name='菜单', help_text='关联的菜单')

    class Meta:
        unique_together = ('role', 'menu')
        verbose_name = '角色菜单映射'
        verbose_name_plural = verbose_name
        db_table_comment = "角色与菜单关系映射表"
