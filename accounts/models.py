from django.db import models
from django.conf import settings
from core.models import BaseModel
# from organizations.models import Merchant
# from payment_channels.models import PaymentSubject
# from settlements.models import PaymentOrder

class Account(BaseModel):
    STATUS_CHOICES = [
        (1, '正常'),
        (0, '冻结'),
        (2, '注销'),
    ]
    merchant = models.ForeignKey(
        'organizations.Merchant',
        on_delete=models.PROTECT,
        verbose_name='所属商户',
        help_text='此账户属于哪个商户'
    )
    # An account could be specific to a payment subject (e.g. a specific bank card of the merchant used for funding)
    # Or it could be a more general platform account for the merchant.
    # The current model links it to a PaymentSubject, implying it's an account related to a specific outward payment capability.
    # If it's a general "wallet" for the merchant on the platform, this might need adjustment.
    # For now, sticking to the plan: "商户在特定支付主体的账户"
    payment_subject = models.OneToOneField(
        'payment_channels.PaymentSubject',
        on_delete=models.PROTECT, # If the payment subject is deleted, this account might be invalid.
        verbose_name='关联支付主体',
        help_text='此账户关联到哪个支付主体（如特定银行卡或第三方支付账户）'
    )
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0.00, verbose_name='账户余额', help_text='总余额，包括可用和冻结部分')
    available_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0.00, verbose_name='可用余额', help_text='可用于支付或提现的余额')
    frozen_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0.00, verbose_name='冻结余额', help_text='因特定操作（如支付冻结、提现申请）被临时冻结的金额')
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=1, verbose_name='账户状态', help_text='1-正常, 0-冻结, 2-注销')
    # account_type = models.CharField(max_length=50, default='settlement_account', verbose_name='账户类型') # e.g., settlement, fee, margin

    class Meta:
        verbose_name = '商户账户'
        verbose_name_plural = verbose_name
        unique_together = (('merchant', 'payment_subject'),)
        db_table_comment = "商户在特定支付主体的资金账户表"

class Withdrawal(BaseModel):
    STATUS_CHOICES = [
        (0, '申请中'), (1, '处理中'), (2, '成功'), (3, '失败'), (4, '已取消'), (5, '审核拒绝')
    ]
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name='提现账户', help_text='从哪个商户账户提现')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='提现金额')
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=0, verbose_name='提现状态', help_text='0-申请中, 1-处理中, 2-成功, 3-失败, 4-已取消, 5-审核拒绝')
    target_account_name = models.CharField(max_length=255, verbose_name='提现至账户名', help_text='收款方银行账户名称（应加密）')
    target_account_number = models.CharField(max_length=100, verbose_name='提现至账号', help_text='收款方银行账号（应加密）')
    bank_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='银行名称')
    remark = models.TextField(null=True, blank=True, verbose_name='备注')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间', help_text='提现成功或最终失败的时间')
    # fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='提现手续费')
    # channel_transaction_id = models.CharField(max_length=128, null=True, blank=True, verbose_name='渠道交易号')

    class Meta:
        verbose_name = '提现记录'
        verbose_name_plural = verbose_name
        db_table_comment = "商户提现申请记录表"

class TransactionLedger(BaseModel):
    TRANSACTION_TYPE_CHOICES = [
        (1, '充值'), (2, '提现'), (3, '支付'), (4, '退款'),
        (5, '服务费收取'), (6, '服务费退回'),
        (7, '账户冻结'), (8, '账户解冻'), # e.g. for withdrawal request
        (9, '系统调账增'), (10, '系统调账减'),
        (11, '支付失败解冻'), # When a payment fails and frozen amount is returned to available
        (12, '提现失败解冻'), # When a withdrawal fails and frozen amount is returned
    ]
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name='关联账户', help_text='资金变动发生在哪一个账户')
    related_order = models.ForeignKey(
        'settlements.PaymentOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='关联支付订单',
        help_text='与此流水相关的支付订单（若有）'
    )
    related_withdrawal = models.ForeignKey(
        Withdrawal,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='关联提现',
        help_text='与此流水相关的提现记录（若有）'
    )
    # related_recharge = models.ForeignKey('Recharge', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联充值')
    transaction_type = models.SmallIntegerField(choices=TRANSACTION_TYPE_CHOICES, verbose_name='流水类型', help_text='说明资金变动的业务性质')
    amount = models.DecimalField(max_digits=18, decimal_places=2, verbose_name='变动金额', help_text='正数表示增加，负数表示减少')
    balance_before = models.DecimalField(max_digits=18, decimal_places=2, verbose_name='变动前余额', help_text='此流水发生前的账户总余额')
    balance_after = models.DecimalField(max_digits=18, decimal_places=2, verbose_name='变动后余额', help_text='此流水发生后的账户总余额')
    available_balance_before = models.DecimalField(max_digits=18, decimal_places=2, default=0.00, verbose_name='变动前可用余额')
    available_balance_after = models.DecimalField(max_digits=18, decimal_places=2, default=0.00, verbose_name='变动后可用余额')
    frozen_balance_before = models.DecimalField(max_digits=18, decimal_places=2, default=0.00, verbose_name='变动前冻结余额')
    frozen_balance_after = models.DecimalField(max_digits=18, decimal_places=2, default=0.00, verbose_name='变动后冻结余额')
    remark = models.TextField(null=True, blank=True, verbose_name='流水备注')
    # operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='操作员')

    class Meta:
        verbose_name = '账户资金流水'
        verbose_name_plural = verbose_name
        db_table_comment = "记录账户余额变动的详细流水"

class ServiceFee(BaseModel):
    STATUS_CHOICES = [
        (1, '已收取'), (2, '已退回'), (0, '待收取'), (3, '收取失败')
    ]
    payment_order = models.OneToOneField(
        'settlements.PaymentOrder',
        on_delete=models.PROTECT, # If order is deleted, this fee record might be an issue or should be archived.
        verbose_name='关联支付订单',
        help_text='此服务费针对哪个支付订单收取'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='服务费金额')
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=0, verbose_name='状态', help_text='1-已收取, 2-已退回, 0-待收取, 3-收取失败')
    collected_at = models.DateTimeField(null=True, blank=True, verbose_name='收取/退回时间')
    # calculation_details = models.JSONField(null=True, blank=True, verbose_name='计费详情', help_text='如费率、固定费用等')

    class Meta:
        verbose_name = '服务费记录'
        verbose_name_plural = verbose_name
        db_table_comment = "支付订单的服务费记录表"

class RechargeInvoice(BaseModel):
    INVOICE_TYPE_CHOICES = [(1, '电子普票'), (2, '纸质专票'), (3, '电子专票')]
    STATUS_CHOICES = [(0, '申请中'), (1, '已开具'), (2, '已邮寄/发送'), (3, '申请驳回')]

    merchant = models.ForeignKey(
        'organizations.Merchant',
        on_delete=models.PROTECT,
        verbose_name='申请商户',
        help_text='哪个商户申请的发票'
    )
    # Assuming TransactionLedger entry for recharge exists and is identifiable
    transaction_ledger = models.ForeignKey(
        TransactionLedger,
        on_delete=models.PROTECT,
        limit_choices_to={'transaction_type': 1}, # Ensure it's a recharge transaction
        verbose_name='关联充值流水',
        help_text='关联到具体的充值交易流水'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='发票金额')
    invoice_type = models.SmallIntegerField(choices=INVOICE_TYPE_CHOICES, default=1, verbose_name='发票类型', help_text='1-电子普票, 2-纸质专票, 3-电子专票')
    title = models.CharField(max_length=255, verbose_name='发票抬头')
    tax_number = models.CharField(max_length=50, null=True, blank=True, verbose_name='税号', help_text='企业发票需要提供税号')
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=0, verbose_name='开票状态', help_text='0-申请中, 1-已开具, 2-已邮寄/发送, 3-申请驳回')
    invoice_number = models.CharField(max_length=50, null=True, blank=True, verbose_name='发票号码')
    invoice_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='发票代码')
    # invoice_file = models.ForeignKey('core.OssFile', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='发票文件')
    # mail_address = models.TextField(null=True, blank=True, verbose_name='邮寄地址（纸质）')
    # email_address = models.EmailField(null=True, blank=True, verbose_name='接收邮箱（电子）')
    # rejection_reason = models.TextField(null=True, blank=True, verbose_name='驳回原因')

    class Meta:
        verbose_name = '充值发票'
        verbose_name_plural = verbose_name
        db_table_comment = "商户充值后申请发票的记录表"

class ElectronicReceipt(BaseModel):
    payment_order = models.OneToOneField(
        'settlements.PaymentOrder',
        on_delete=models.CASCADE, # If order is deleted, receipt is too.
        verbose_name='关联支付订单',
        help_text='此电子回单对应哪个支付订单'
    )
    receipt_file_url = models.URLField(max_length=1024, null=True, blank=True, verbose_name='电子回单文件URL', help_text='指向存储在OSS等的文件链接')
    # Alternatively, link to OssFile model:
    # receipt_file = models.ForeignKey('core.OssFile', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='电子回单文件')
    generated_at = models.DateTimeField(null=True, blank=True, verbose_name='生成时间')
    # receipt_number = models.CharField(max_length=100, null=True, blank=True, unique=True, verbose_name='回单编号')

    class Meta:
        verbose_name = '电子回单'
        verbose_name_plural = verbose_name
        db_table_comment = "支付订单的电子回单记录表"
