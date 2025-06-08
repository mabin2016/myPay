from django.db import models
from django.conf import settings
from core.models import BaseModel
# Import related models using string notation to avoid circular imports if necessary
# from organizations.models import Merchant
# from users.models import User
# from payment_channels.models import PaymentChannel, ArrivalChannel, PaymentSubject, OrderRule
from .choices import BatchStatus, OrderStatus, ServiceFeeStatus # Import custom choices

class PaymentBatch(BaseModel):
    batch_number = models.CharField(max_length=64, unique=True, verbose_name='批次号', help_text='系统生成的唯一批次号')
    merchant = models.ForeignKey(
        'organizations.Merchant',
        on_delete=models.PROTECT,
        verbose_name='所属商户',
        help_text='此支付批次属于哪个商户'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_batches',
        verbose_name='上传经办人',
        help_text='通过系统上传此批次的用户'
    )
    total_orders = models.IntegerField(default=0, verbose_name='订单总数')
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0.00, verbose_name='订单总金额')
    status = models.SmallIntegerField(choices=BatchStatus.CHOICES, default=BatchStatus.UNCHECKED, verbose_name='批次状态', help_text='表示当前批次的处理阶段')
    remark = models.TextField(null=True, blank=True, verbose_name='备注')
    audit_history = models.JSONField(null=True, blank=True, verbose_name='审核历史', help_text='例如: [{"auditor_id": 1, "timestamp": "YYYY-MM-DDTHH:MM:SSZ", "action": "approve_initial_audit", "remark": "OK"}]')
    # source_file = models.ForeignKey('core.OssFile', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='源文件')

    class Meta:
        verbose_name = '支付批次'
        verbose_name_plural = verbose_name
        db_table_comment = "商户上传的支付批次主表"

class SubPaymentBatch(BaseModel):
    # STATUS_CHOICES for SubPaymentBatch can also use a dedicated choices class if complex
    # For now, keeping it simple if its lifecycle is simpler.
    # Or potentially reuse some statuses from BatchStatus or OrderStatus if applicable and clearly defined.
    SUB_BATCH_STATUS_CHOICES = [
        (0, '待处理'), (1, '处理中'), (2, '部分成功'), (3, '全部成功'), (4, '失败'), (5, '已取消')
    ]
    parent_batch = models.ForeignKey(
        PaymentBatch,
        on_delete=models.CASCADE,
        related_name='sub_batches',
        verbose_name='父批次',
        help_text='关联的主支付批次'
    )
    sub_batch_number = models.CharField(max_length=64, unique=True, verbose_name='子批次号', help_text='按规则拆分后生成的唯一子批次号')
    payment_channel = models.ForeignKey(
        'payment_channels.PaymentChannel',
        on_delete=models.PROTECT,
        verbose_name='支付渠道',
        help_text='此子批次将通过哪个支付渠道处理'
    )
    total_orders = models.IntegerField(default=0, verbose_name='订单总数')
    total_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0.00, verbose_name='订单总金额')
    status = models.SmallIntegerField(choices=SUB_BATCH_STATUS_CHOICES, default=0, verbose_name='子批次支付状态', help_text='表示当前子批次的处理阶段')
    # payment_request_time = models.DateTimeField(null=True, blank=True, verbose_name='请求支付时间')
    # payment_response_time = models.DateTimeField(null=True, blank=True, verbose_name='支付响应时间')
    # channel_batch_id = models.CharField(max_length=128, null=True, blank=True, verbose_name='渠道批次号') # If channel supports batch submission

    class Meta:
        verbose_name = '子支付批次'
        verbose_name_plural = verbose_name
        db_table_comment = "按支付渠道或限额拆分后的子批次表"

class PaymentOrder(BaseModel):
    order_number = models.CharField(max_length=64, unique=True, verbose_name='订单号', help_text='系统生成的唯一订单号')
    payment_batch = models.ForeignKey(
        PaymentBatch,
        on_delete=models.CASCADE, # If batch is deleted, orders are too. Or PROTECT if orders need to be kept.
        related_name='orders',
        verbose_name='所属支付批次'
    )
    sub_payment_batch = models.ForeignKey(
        SubPaymentBatch,
        on_delete=models.SET_NULL, # If sub-batch is deleted, order might be re-assigned or orphaned.
        null=True, blank=True,
        related_name='orders',
        verbose_name='所属子支付批次'
    )
    merchant = models.ForeignKey(
        'organizations.Merchant',
        on_delete=models.PROTECT,
        verbose_name='所属商户'
    )
    payment_subject = models.ForeignKey(
        'payment_channels.PaymentSubject',
        on_delete=models.PROTECT,
        verbose_name='支付主体',
        help_text='实际出款的支付主体（如银行账户或第三方支付商户号）'
    )
    recipient_name = models.CharField(max_length=255, verbose_name='收款人姓名', help_text='应加密存储')
    recipient_account = models.CharField(max_length=100, verbose_name='收款账号', help_text='银行卡号、支付宝账号等，应加密存储')
    recipient_bank_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='收款银行名称')
    recipient_bank_branch = models.CharField(max_length=100, null=True, blank=True, verbose_name='收款银行支行')
    recipient_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name='收款人手机号', help_text='应加密存储')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='支付金额')

    payment_channel_used = models.ForeignKey(
        'payment_channels.PaymentChannel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='实际使用支付渠道',
        help_text='最终实际执行支付的渠道'
    )
    arrival_channel_used = models.ForeignKey(
        'payment_channels.ArrivalChannel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='实际使用到账通道',
        help_text='最终实际的到账方式'
    )
    status = models.SmallIntegerField(choices=OrderStatus.CHOICES, default=OrderStatus.UNCHECKED, verbose_name='订单状态', help_text='表示当前订单的处理阶段')
    remark = models.TextField(null=True, blank=True, verbose_name='备注')
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息', help_text='记录支付失败或校验失败的原因')

    frozen_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='冻结金额', help_text='因特定原因（如风控）被冻结的金额')
    is_frozen = models.BooleanField(default=False, verbose_name='是否冻结', help_text='标记此订单金额是否被冻结')

    service_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='服务费金额')
    service_fee_frozen = models.BooleanField(default=False, verbose_name='服务费是否冻结')
    service_fee_status = models.SmallIntegerField(choices=ServiceFeeStatus.CHOICES, default=ServiceFeeStatus.NOT_CHARGED, verbose_name='服务费状态', help_text='服务费的收取状态')

    payment_time = models.DateTimeField(null=True, blank=True, verbose_name='支付成功时间')
    channel_transaction_id = models.CharField(max_length=128, null=True, blank=True, verbose_name='渠道交易号', help_text='支付渠道返回的交易流水号')
    applied_rule = models.ForeignKey(
        'payment_channels.OrderRule',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='应用的订单规则',
        help_text='此订单在处理过程中触发并应用了哪个规则'
    )
    retries_count = models.PositiveSmallIntegerField(default=0, verbose_name='重试次数', help_text='订单支付的重试次数')
    # priority = models.IntegerField(default=0, verbose_name='支付优先级', help_text='数字越大优先级越高')
    # expected_arrival_time = models.DateTimeField(null=True, blank=True, verbose_name='预计到账时间')
    # settlement_type = models.SmallIntegerField(default=1, verbose_name='结算类型', help_text='例如：1-T+0, 2-T+1')


    class Meta:
        verbose_name = '支付订单'
        verbose_name_plural = verbose_name
        db_table_comment = "支付订单详细信息表"
        indexes = [
            models.Index(fields=['status', 'payment_channel_used']),
            models.Index(fields=['merchant', 'created_at']),
        ]
