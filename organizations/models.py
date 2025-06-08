from django.db import models
from django.conf import settings
from core.models import BaseModel

class SigningCompany(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name='签约公司名称')
    company_code = models.CharField(max_length=100, unique=True, verbose_name='公司代码')
    address = models.CharField(max_length=500, null=True, blank=True, verbose_name='公司地址')
    contact_person = models.CharField(max_length=100, null=True, blank=True, verbose_name='联系人')
    contact_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name='联系电话')
    status_choices = [
        (1, '正常'),
        (0, '禁用'),
    ]
    status = models.SmallIntegerField(choices=status_choices, default=1, verbose_name='状态', help_text='例如：1-正常，0-禁用')

    class Meta:
        verbose_name = '签约公司'
        verbose_name_plural = verbose_name
        db_table_comment = "签约公司信息表"

class Group(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name='集团名称')
    group_code = models.CharField(max_length=100, unique=True, verbose_name='集团代码')
    description = models.TextField(null=True, blank=True, verbose_name='集团描述')

    class Meta:
        verbose_name = '集团'
        verbose_name_plural = verbose_name
        db_table_comment = "集团信息表"

class Merchant(BaseModel):
    status_choices = [
        (1, '待签约'), # Initial state perhaps
        (2, '已签约'), # Active
        (3, '已注销'), # Inactive / Closed
        (4, '审核中'),
        (5, '审核拒绝'),
    ]
    name = models.CharField(max_length=255, verbose_name='商户名称')
    merchant_code = models.CharField(max_length=100, unique=True, verbose_name='商户代码', help_text='系统生成的唯一商户标识')
    signing_company = models.ForeignKey(
        SigningCompany,
        on_delete=models.PROTECT,
        verbose_name='所属签约公司',
        help_text='该商户签约主体公司'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='所属集团',
        help_text='商户所属的集团（可选）'
    )
    # A merchant is operated by a user, this user is the admin for this merchant account on the platform.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT, # Or models.SET_NULL if user deletion should not delete merchant
        verbose_name='关联平台用户',
        help_text='关联到平台的管理员用户，用于操作此商户的业务'
    )
    status = models.SmallIntegerField(choices=status_choices, default=1, verbose_name='状态', help_text='例如：1-待签约，2-已签约，3-已注销')
    contract_info = models.TextField(null=True, blank=True, verbose_name='签约信息', help_text='JSON格式存储合同编号、有效期等')
    # business_license_image = models.ForeignKey('core.OssFile', on_delete=models.SET_NULL, null=True, blank=True, related_name='merchant_license', verbose_name='营业执照图片')
    # legal_person_id_front_image = models.ForeignKey('core.OssFile', on_delete=models.SET_NULL, null=True, blank=True, related_name='merchant_legal_id_front', verbose_name='法人身份证正面')
    # legal_person_id_back_image = models.ForeignKey('core.OssFile', on_delete=models.SET_NULL, null=True, blank=True, related_name='merchant_legal_id_back', verbose_name='法人身份证反面')


    class Meta:
        verbose_name = '商户'
        verbose_name_plural = verbose_name
        db_table_comment = "商户信息表"
        unique_together = [['signing_company', 'name']] # A signing company should not have two merchants with the same name

class Platform(BaseModel):
    name = models.CharField(max_length=100, default='综合结算平台', verbose_name='平台名称')
    version = models.CharField(max_length=50, verbose_name='平台版本', help_text='例如：1.0.0')
    # contact_email = models.EmailField(null=True, blank=True, verbose_name='平台联系邮箱')
    # website_url = models.URLField(null=True, blank=True, verbose_name='平台网址')

    class Meta:
        verbose_name = '平台信息'
        verbose_name_plural = verbose_name
        db_table_comment = "平台基本信息表（通常只有一条记录）"

    def save(self, *args, **kwargs):
        # Enforce a single platform entry if this model is used for global platform settings
        if not self.pk and Platform.objects.exists():
            # Do not save if an instance already exists
            raise Exception("Only one Platform record is allowed.")
        super(Platform, self).save(*args, **kwargs)
