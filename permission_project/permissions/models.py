from django.db import models
from django.contrib.auth.models import User

class Permission(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="权限名称，例如：查看用户列表")
    code = models.CharField(max_length=100, unique=True, help_text="权限编码，用于程序判断，例如：view_user_list")
    url = models.CharField(max_length=255, blank=True, null=True, help_text="相关URL，可选，用于前端菜单或后端接口匹配")
    description = models.TextField(blank=True, null=True, help_text="权限描述")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "页面权限"
        verbose_name_plural = verbose_name
        ordering = ['id']

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="角色名称，例如：管理员")
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles", help_text="角色拥有的页面权限")
    users = models.ManyToManyField(User, blank=True, related_name="roles", help_text="拥有此角色的用户")
    description = models.TextField(blank=True, null=True, help_text="角色描述")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = verbose_name
        ordering = ['id']

# --- Data Permission Models ---

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="签约公司名称")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "签约公司"
        verbose_name_plural = verbose_name
        ordering = ['name']

class Group(models.Model):
    company = models.ForeignKey(Company, related_name='groups', on_delete=models.CASCADE, help_text="所属签约公司")
    name = models.CharField(max_length=255, help_text="集团名称")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.name} - {self.name}"

    class Meta:
        verbose_name = "集团"
        verbose_name_plural = verbose_name
        unique_together = ('company', 'name')
        ordering = ['company', 'name']

class Enterprise(models.Model):
    group = models.ForeignKey(Group, related_name='enterprises', on_delete=models.CASCADE, help_text="所属集团")
    name = models.CharField(max_length=255, help_text="企业名称")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.group.name} - {self.name}"

    class Meta:
        verbose_name = "企业"
        verbose_name_plural = verbose_name
        unique_together = ('group', 'name')
        ordering = ['group', 'name']

class DataPermissionCollection(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="数据权限集合名称，例如：业务数据")
    code = models.CharField(max_length=100, unique=True, help_text="数据权限集合编码，例如：business_data")
    description = models.TextField(blank=True, null=True, help_text="数据权限集合描述")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "数据权限集合"
        verbose_name_plural = verbose_name
        ordering = ['name']

class UserCompanyAdminPermission(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_admin_permission', help_text="用户")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='admin_users', help_text="管理的签约公司")
    # is_admin field is implicitly True by existence of this record.
    # If a user can be admin of multiple companies, this should be ForeignKey to User.
    # For now, assuming a user is admin of AT MOST one company directly via this model.
    # Or, if a user can be admin of multiple companies, this model should be:
    # user = models.ForeignKey(User, on_delete=models.CASCADE)
    # company = models.ForeignKey(Company, on_delete=models.CASCADE)
    # class Meta:
    #    unique_together = ('user', 'company')
    # For the initial requirement: "如果选择’签约公司管理员‘这个选项...就不能选择其他权限配置"
    # This implies a user is either a "Super Company Admin" or has granular perms.
    # Let's refine this. A user can be marked as an admin for *a specific* company.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} is admin of {self.company.name}"

    class Meta:
        verbose_name = "签约公司管理员权限"
        verbose_name_plural = verbose_name
        unique_together = ('user', 'company') # User can be admin of one company through this table.

class UserGroupAdminPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_admin_permissions', help_text="用户")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='admin_users', help_text="管理的集团")
    # is_admin field is implicitly True.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} is admin of group {self.group.name}"

    class Meta:
        verbose_name = "集团管理员权限"
        verbose_name_plural = verbose_name
        unique_together = ('user', 'group')

class UserEnterpriseDataPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enterprise_data_permissions', help_text="用户")
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name='user_permissions', help_text="关联的企业")
    data_permissions = models.ManyToManyField(
        DataPermissionCollection,
        blank=True,
        related_name="user_enterprise_assignments",
        help_text="在该企业拥有的数据权限集合"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Data permissions for {self.user.username} in {self.enterprise.name}"

    class Meta:
        verbose_name = "用户企业数据权限"
        verbose_name_plural = verbose_name
        unique_together = ('user', 'enterprise')
        ordering = ['user', 'enterprise']
