# Status choices for PaymentBatch model
class BatchStatus:
    UNCHECKED = 0                 # 批次刚上传，未进行任何校验
    VALIDATING_FORMAT = 1         # 系统正在进行格式校验
    FORMAT_VALIDATION_FAILED = 2  # 格式校验失败（部分或全部订单）
    FORMAT_VALIDATION_SUCCESS = 3 # 格式校验全部通过
    PENDING_INITIAL_AUDIT = 4     # 待初审 (格式校验通过后，或需要人工介入的批次)
    INITIAL_AUDIT_APPROVED = 5    # 初审通过
    INITIAL_AUDIT_REJECTED = 6    # 初审拒绝
    PENDING_FINAL_AUDIT = 7       # 待复审 (初审通过后)
    FINAL_AUDIT_APPROVED = 8      # 复审通过 (此时批次状态可视为“待支付处理”或“待拆分”)
    FINAL_AUDIT_REJECTED = 9      # 复审拒绝
    PROCESSING_PAYMENT = 10       # 系统正在处理支付（已发送给支付渠道，等待回调）
    PARTIALLY_PAID = 11           # 部分支付成功 (批次中有成功也有失败的订单)
    FULLY_PAID = 12               # 全部支付成功
    PAYMENT_FAILED = 13           # 支付失败 (批次中所有可支付订单都失败，或关键错误)
    CANCELLED = 14                # 已作废/已取消 (用户或系统取消)
    PENDING_VALIDATION = 15       # 批次已上传，格式校验通过，等待其他业务校验（银行要素，风控等）
    VALIDATION_FAILED = 16        # 业务校验失败（银行要素，风控等）
    VALIDATION_SUCCESS = 17       # 业务校验成功 (等同于格式校验成功后的状态，可以合并或作为独立步骤)


    CHOICES = [
        (UNCHECKED, '未校验'),
        (VALIDATING_FORMAT, '格式校验中'),
        (FORMAT_VALIDATION_FAILED, '格式校验失败'),
        (FORMAT_VALIDATION_SUCCESS, '格式校验成功'),
        (PENDING_INITIAL_AUDIT, '待初审'),
        (INITIAL_AUDIT_APPROVED, '初审通过'),
        (INITIAL_AUDIT_REJECTED, '初审拒绝'),
        (PENDING_FINAL_AUDIT, '待复审'),
        (FINAL_AUDIT_APPROVED, '复审通过/待支付'),
        (FINAL_AUDIT_REJECTED, '复审拒绝'),
        (PROCESSING_PAYMENT, '支付处理中'),
        (PARTIALLY_PAID, '部分支付成功'),
        (FULLY_PAID, '全部支付成功'),
        (PAYMENT_FAILED, '支付失败'),
        (CANCELLED, '已作废/取消'),
        (PENDING_VALIDATION, '待业务校验'),
        (VALIDATION_FAILED, '业务校验失败'),
        (VALIDATION_SUCCESS, '业务校验成功'),
    ]

# Status choices for PaymentOrder model
class OrderStatus:
    UNCHECKED = 0                   # 订单刚创建，未进行任何校验
    FORMAT_VALIDATION_PENDING = 1   # 待格式校验
    FORMAT_VALIDATION_SUCCESS = 2   # 格式校验通过
    FORMAT_VALIDATION_FAILED = 3    # 格式校验失败
    BANK_ELEMENT_VALIDATION_PENDING = 4 # 待银行要素校验 (三要素/四要素)
    BANK_ELEMENT_VALIDATION_SUCCESS = 5 # 银行要素校验通过
    BANK_ELEMENT_VALIDATION_FAILED = 6  # 银行要素校验失败
    RISK_CONTROL_PENDING = 7        # 待风控校验
    RISK_CONTROL_APPROVED = 8       # 风控通过
    RISK_CONTROL_REJECTED = 9       # 风控拒绝 (例如疑似欺诈，或超限额)
    DGE_VALIDATION_PENDING = 10     # 待董监高名单校验
    DGE_VALIDATION_APPROVED = 11    # 董监高名单通过
    DGE_VALIDATION_REJECTED = 12    # 董监高名单拒绝
    PENDING_PAYMENT = 13            # 待支付 (所有校验完成，已加入支付队列)
    PAYMENT_IN_PROGRESS = 14        # 支付中 (已提交给支付渠道)
    PAYMENT_SUCCESSFUL = 15         # 支付成功
    PAYMENT_FAILED = 16             # 支付失败 (渠道返回失败)
    PAYMENT_UNKNOWN = 17            # 支付状态未知 (需要查询确认)
    CANCELLED = 18                  # 已取消
    FROZEN = 19                     # 已冻结 (例如风控挂起)
    REFUND_PENDING = 20             # 退款中
    REFUNDED = 21                   # 已退款
    PARTIALLY_REFUNDED = 22         # 部分退款

    CHOICES = [
        (UNCHECKED, '未校验'),
        (FORMAT_VALIDATION_PENDING, '待格式校验'),
        (FORMAT_VALIDATION_SUCCESS, '格式校验成功'),
        (FORMAT_VALIDATION_FAILED, '格式校验失败'),
        (BANK_ELEMENT_VALIDATION_PENDING, '待银行要素校验'),
        (BANK_ELEMENT_VALIDATION_SUCCESS, '银行要素校验成功'),
        (BANK_ELEMENT_VALIDATION_FAILED, '银行要素校验失败'),
        (RISK_CONTROL_PENDING, '待风控校验'),
        (RISK_CONTROL_APPROVED, '风控通过'),
        (RISK_CONTROL_REJECTED, '风控拒绝'),
        (DGE_VALIDATION_PENDING, '待董监高校验'),
        (DGE_VALIDATION_APPROVED, '董监高通过'),
        (DGE_VALIDATION_REJECTED, '董监高拒绝'),
        (PENDING_PAYMENT, '待支付'),
        (PAYMENT_IN_PROGRESS, '支付中'),
        (PAYMENT_SUCCESSFUL, '支付成功'),
        (PAYMENT_FAILED, '支付失败'),
        (PAYMENT_UNKNOWN, '支付状态未知'),
        (CANCELLED, '已取消'),
        (FROZEN, '已冻结'),
        (REFUND_PENDING, '退款中'),
        (REFUNDED, '已退款'),
        (PARTIALLY_REFUNDED, '部分退款'),
    ]

# Status choices for PaymentOrder.service_fee_status
class ServiceFeeStatus:
    NOT_CHARGED = 0     # 未收取
    CHARGED = 1         # 已收取
    REFUNDED = 2        # 已退回 (e.g. main transaction was refunded)
    CHARGE_FAILED = 3   # 收取失败 (e.g. insufficient balance in fee account if separate)
    # PENDING_REFUND = 4  # 待退回 (if service fee refund is an async process)

    CHOICES = [
        (NOT_CHARGED, '服务费未收取'),
        (CHARGED, '服务费已收取'),
        (REFUNDED, '服务费已退回'),
        (CHARGE_FAILED, '服务费收取失败'),
        # (PENDING_REFUND, '服务费待退回'),
    ]

# It's good practice to also update the status fields in models.py
# to use these choices, e.g.:
# status = models.SmallIntegerField(choices=BatchStatus.CHOICES, default=BatchStatus.UNCHECKED, verbose_name='批次状态')
# status = models.SmallIntegerField(choices=OrderStatus.CHOICES, default=OrderStatus.UNCHECKED, verbose_name='订单状态')
# service_fee_status = models.SmallIntegerField(choices=ServiceFeeStatus.CHOICES, default=ServiceFeeStatus.NOT_CHARGED, verbose_name='服务费状态')
