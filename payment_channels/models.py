from django.db import models
from core.models import BaseModel
# from organizations.models import SigningCompany # This will cause circular import if SigningCompany imports anything from here. Use string reference.

class PaymentChannel(BaseModel):
    name = models.CharField(max_length=100, unique=True, verbose_name='支付渠道名称', help_text='如：支付宝ISV, 微信支付, 银行卡快捷')
    channel_code = models.CharField(max_length=50, unique=True, verbose_name='渠道代码', help_text='如：ALIPAY_ISV, WECHAT_PAY, BANK_QUICKPAY')
    is_active = models.BooleanField(default=True, verbose_name='是否激活', help_text='标记此支付渠道是否可用')
    config_details = models.JSONField(null=True, blank=True, verbose_name='渠道配置详情', help_text='存储API密钥、证书路径、回调地址等敏感信息（应加密存储或引用安全存储）')
    # logo = models.ForeignKey('core.OssFile', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='渠道Logo')

    class Meta:
        verbose_name = '支付渠道'
        verbose_name_plural = verbose_name
        db_table_comment = "支付渠道基础信息表"

class ArrivalChannel(BaseModel):
    payment_channel = models.ForeignKey(
        PaymentChannel,
        on_delete=models.PROTECT,
        verbose_name='所属支付渠道',
        help_text='此到账通道属于哪个主支付渠道'
    )
    name = models.CharField(max_length=100, verbose_name='到账通道名称', help_text='如：银行卡（借记卡）, 支付宝余额, 微信零钱')
    channel_code = models.CharField(max_length=50, verbose_name='到账通道代码', help_text='如：BANK_DEBIT, ALIPAY_BALANCE, WECHAT_WALLET. 应确保在所属支付渠道下唯一')
    is_active = models.BooleanField(default=True, verbose_name='是否激活', help_text='标记此到账通道是否可用')
    # fee_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.00, verbose_name='手续费率', help_text='例如0.006代表0.6%')
    # min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.01, verbose_name='最小交易金额')
    # max_amount = models.DecimalField(max_digits=12, decimal_places=2, default=50000.00, verbose_name='最大交易金额')


    class Meta:
        verbose_name = '到账通道'
        verbose_name_plural = verbose_name
        unique_together = (('payment_channel', 'channel_code'),)
        db_table_comment = "支付渠道下的具体到账方式"

class PaymentSubject(BaseModel):
    signing_company = models.ForeignKey(
        'organizations.SigningCompany',
        on_delete=models.PROTECT,
        verbose_name='所属签约公司',
        help_text='此支付主体属于哪个签约公司'
    )
    payment_channel = models.ForeignKey(
        PaymentChannel,
        on_delete=models.PROTECT,
        verbose_name='支付渠道',
        help_text='此支付主体关联的支付渠道'
    )
    subject_name = models.CharField(max_length=200, verbose_name='支付主体名称', help_text='例如：XX公司支付宝账户')
    account_name = models.CharField(max_length=200, verbose_name='付款账户名称', help_text='银行开户名或第三方支付账户名')
    account_number = models.CharField(max_length=100, verbose_name='付款账号', help_text='银行卡号或第三方支付账号（应加密存储）')
    is_default = models.BooleanField(default=False, verbose_name='是否默认支付主体', help_text='标记是否为所属签约公司在该渠道下的默认支付主体')
    configs = models.JSONField(verbose_name='支付配置', help_text='特定于此主体的支付配置，如API子商户ID、公私钥、特定API地址等（应加密存储）')
    # daily_limit = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name='日累计限额')
    # single_transaction_limit = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name='单笔限额')

    class Meta:
        verbose_name = '支付主体'
        verbose_name_plural = verbose_name
        unique_together = (('signing_company', 'payment_channel', 'account_number'),) #确保同一签约公司，同一渠道下账号唯一
        db_table_comment = "签约公司在各支付渠道的支付主体账户信息"

class OrderRule(BaseModel):
    RULE_TYPE_CHOICES = [
        (1, '转换提示'), # E.g., if amount too high, suggest alternative
        (2, '订单挂起'), # E.g., for manual review
        (3, '订单重发'), # E.g., for transient errors
        (4, '渠道切换'), # E.g., if one channel fails, try another
    ]
    name = models.CharField(max_length=100, verbose_name='规则名称', unique=True)
    rule_type = models.SmallIntegerField(choices=RULE_TYPE_CHOICES, verbose_name='规则类型', help_text='1-转换提示, 2-订单挂起, 3-订单重发, 4-渠道切换')
    config = models.JSONField(null=True, blank=True, verbose_name='规则配置', help_text='例如重发间隔、次数；切换目标渠道；挂起原因等')
    is_active = models.BooleanField(default=True, verbose_name='是否激活', help_text='标记此规则是否生效')
    # priority = models.IntegerField(default=0, verbose_name='优先级', help_text='数字越大优先级越高')
    # conditions = models.JSONField(null=True, blank=True, verbose_name='触发条件', help_text='定义规则何时被触发，例如特定错误码、金额范围等')


    class Meta:
        verbose_name = '订单处理规则'
        verbose_name_plural = verbose_name
        db_table_comment = "支付订单处理规则配置表"
