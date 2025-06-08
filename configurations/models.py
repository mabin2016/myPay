from django.db import models
from core.models import BaseModel

class RiskControlConfig(BaseModel):
    CONFIG_TYPE_CHOICES = [
        (1, '金额上限'),        # Max amount per transaction, per day, per month
        (2, '收款人限制'),      # Blacklist/Whitelist of recipient accounts/names
        (3, '频率限制'),        # Max transactions per minute/hour
        (4, 'IP地址限制'),      # Allowed IPs for API calls or logins
        (5, '地理位置限制'),    # Allowed countries/regions for payments
        (6, '设备指纹限制'),    # Limit operations from specific devices
        (7, '支付渠道风控'),    # Specific rules for a payment channel
        (99, '其他'),
    ]
    name = models.CharField(max_length=255, unique=True, verbose_name='风控规则名称', help_text='例如：单日最大交易金额限制')
    config_type = models.SmallIntegerField(choices=CONFIG_TYPE_CHOICES, verbose_name='配置类型', help_text='风控规则的具体类别')
    rules = models.JSONField(verbose_name='规则详情', help_text='JSON格式存储规则的具体参数，例如：{"max_amount_per_day": 50000, "currency": "CNY"} 或 {"blocked_keywords": ["gambling", "fraud"]}')
    is_active = models.BooleanField(default=True, verbose_name='是否激活', help_text='标记此风控规则是否当前生效')
    # description = models.TextField(null=True, blank=True, verbose_name='规则描述')
    # start_time = models.DateTimeField(null=True, blank=True, verbose_name='生效开始时间')
    # end_time = models.DateTimeField(null=True, blank=True, verbose_name='生效结束时间')
    # target_merchants = models.ManyToManyField('organizations.Merchant', blank=True, verbose_name='适用商户', help_text='此规则适用于哪些商户，不选则为全局')


    class Meta:
        verbose_name = '风控配置'
        verbose_name_plural = verbose_name
        db_table_comment = "系统风控规则配置表"

class WhitelistConfig(BaseModel):
    ID_TYPE_CHOICES = [
        (1, '身份证'),
        (2, '护照'),
        (3, '银行卡号'),
        (4, '手机号'),
        (5, 'IP地址'),
        (99, '其他'),
    ]
    name = models.CharField(max_length=255, verbose_name='白名单名称', help_text='例如：大额交易用户白名单')
    # For 'id_type', it could be recipient ID, payer ID, IP address, etc.
    id_type = models.SmallIntegerField(choices=ID_TYPE_CHOICES, verbose_name='名单项类型', help_text='白名单中记录的标识类型')
    # 'value' should be a more generic term than 'id_number'
    value = models.CharField(max_length=255, verbose_name='白名单值', help_text='具体的白名单号码或地址（建议加密存储敏感信息）')
    description = models.TextField(null=True, blank=True, verbose_name='描述', help_text='关于此白名单项的说明')
    is_active = models.BooleanField(default=True, verbose_name='是否激活', help_text='标记此白名单项是否生效')
    # expires_at = models.DateTimeField(null=True, blank=True, verbose_name='过期时间')

    class Meta:
        verbose_name = '白名单配置'
        verbose_name_plural = verbose_name
        unique_together = (('id_type', 'value'),) # Ensure a value is unique for its type
        db_table_comment = "系统白名单配置表"

class IpConfig(BaseModel):
    ACCESS_TYPE_CHOICES = [
        (1, '允许'),
        (0, '禁止'),
    ]
    ip_address = models.GenericIPAddressField(unique=True, verbose_name='IP地址')
    access_type = models.SmallIntegerField(choices=ACCESS_TYPE_CHOICES, default=1, verbose_name='访问类型', help_text='1-允许访问, 0-禁止访问')
    description = models.TextField(null=True, blank=True, verbose_name='描述', help_text='关于此IP配置的说明，例如所属系统或原因')
    # scope = models.CharField(max_length=100, default='GLOBAL', verbose_name='作用范围', help_text='例如：API, ADMIN_PANEL, MERCHANT_PORTAL')


    class Meta:
        verbose_name = 'IP地址配置'
        verbose_name_plural = verbose_name
        db_table_comment = "系统IP访问控制配置表"

# Consider adding a generic SystemParameter model if many small configurations are needed.
# class SystemParameter(BaseModel):
#     key = models.CharField(max_length=100, unique=True, verbose_name='参数键')
#     value = models.TextField(verbose_name='参数值')
#     description = models.TextField(null=True, blank=True, verbose_name='参数描述')
#     is_active = models.BooleanField(default=True, verbose_name='是否启用')
#
#     class Meta:
#         verbose_name = '系统参数配置'
#         verbose_name_plural = verbose_name
#         db_table_comment = "通用系统参数配置表"
