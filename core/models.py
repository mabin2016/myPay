from django.db import models
from django.conf import settings # Required for ForeignKey to settings.AUTH_USER_MODEL if User model is not yet defined

class BaseModel(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name='ID', help_text='主键，BIGINT UNSIGNED AUTO_INCREMENT')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', help_text='记录创建时间，自动添加')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间', help_text='记录更新时间，自动更新')

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        # Try to return a meaningful name if 'name' attribute exists, else default to PK
        if hasattr(self, 'name') and self.name:
            return str(self.name)
        return f"{self.__class__.__name__} object ({self.pk})"

# Business support models
class SmsRecord(BaseModel):
    phone_number = models.CharField(max_length=20, verbose_name='手机号')
    content = models.TextField(verbose_name='短信内容')
    status = models.SmallIntegerField(default=0, verbose_name='发送状态', help_text='0-待发送, 1-成功, 2-失败')
    response_message = models.TextField(null=True, blank=True, verbose_name='服务商响应')

    class Meta:
        verbose_name = '短信记录'
        verbose_name_plural = verbose_name
        db_table_comment = "短信发送记录表"

class FeishuRecord(BaseModel):
    request_id = models.CharField(max_length=100, null=True, blank=True, verbose_name='请求ID', help_text='飞书API请求的唯一ID')
    target_user = models.CharField(max_length=100, verbose_name='目标用户/群组', help_text='User ID, Open ID, Chat ID等')
    message_type = models.CharField(max_length=50, default='text', verbose_name='消息类型', help_text='例如: text, post, image')
    content = models.JSONField(verbose_name='消息内容', help_text='结构化的消息体，符合飞书API规范')
    status = models.SmallIntegerField(default=0, verbose_name='发送状态', help_text='0-待发送, 1-成功, 2-失败')
    response_code = models.IntegerField(null=True, blank=True, verbose_name='服务商响应码')
    response_message = models.TextField(null=True, blank=True, verbose_name='服务商响应消息')

    class Meta:
        verbose_name = '飞书记录'
        verbose_name_plural = verbose_name
        db_table_comment = "飞书消息发送记录表"

class DingtalkRecord(BaseModel):
    request_id = models.CharField(max_length=100, null=True, blank=True, verbose_name='请求ID', help_text='钉钉API请求的唯一ID')
    target_user = models.CharField(max_length=255, verbose_name='目标用户/群组', help_text='UserID列表, Chat ID等')
    message_type = models.CharField(max_length=50, default='text', verbose_name='消息类型', help_text='例如: text, markdown, action_card')
    content = models.JSONField(verbose_name='消息内容', help_text='结构化的消息体，符合钉钉API规范')
    status = models.SmallIntegerField(default=0, verbose_name='发送状态', help_text='0-待发送, 1-成功, 2-失败')
    response_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='服务商响应码', help_text='钉钉通常返回字符串形式的错误码')
    response_message = models.TextField(null=True, blank=True, verbose_name='服务商响应消息')

    class Meta:
        verbose_name = '钉钉记录'
        verbose_name_plural = verbose_name
        db_table_comment = "钉钉消息发送记录表"

class OssFile(BaseModel):
    file_name = models.CharField(max_length=255, verbose_name='文件名')
    file_url = models.URLField(max_length=1024, unique=True, verbose_name='文件URL')
    file_type = models.CharField(max_length=100, verbose_name='文件类型', help_text='例如：image/jpeg, application/pdf, text/csv')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Use string 'users.User' if direct import is an issue during startup
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='上传用户',
        help_text='关联到上传此文件的用户'
    )

    class Meta:
        verbose_name = 'OSS存储文件'
        verbose_name_plural = verbose_name
        db_table_comment = "对象存储文件记录表"

class ImportExportTask(BaseModel):
    TASK_TYPE_CHOICES = [ (1, '导入'), (2, '导出'), ]
    STATUS_CHOICES = [ (0, '待处理'), (1, '处理中'), (2, '成功'), (3, '失败'), ]

    task_name = models.CharField(max_length=255, verbose_name='任务名称')
    task_type = models.SmallIntegerField(choices=TASK_TYPE_CHOICES, verbose_name='任务类型', help_text='1-导入, 2-导出')
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=0, verbose_name='任务状态', help_text='0-待处理, 1-处理中, 2-成功, 3-失败')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Use string 'users.User'
        on_delete=models.PROTECT,
        verbose_name='创建用户',
        help_text='关联到创建此任务的用户'
    )
    file = models.ForeignKey(
        OssFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='关联文件',
        help_text='导入的文件或导出的结果文件'
    )
    result_message = models.TextField(null=True, blank=True, verbose_name='任务结果信息')

    class Meta:
        verbose_name = '导入导出任务'
        verbose_name_plural = verbose_name
        db_table_comment = "导入导出任务记录表"

class SystemLog(BaseModel):
    LEVEL_CHOICES = [
        ('INFO', '信息'), ('WARNING', '警告'), ('ERROR', '错误'),
        ('CRITICAL', '严重'), ('DEBUG', '调试'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Use string 'users.User'
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='操作用户',
        help_text='执行操作的用户，可为空（如系统自动任务）'
    )
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='INFO', verbose_name='日志级别')
    module = models.CharField(max_length=100, verbose_name='模块', help_text='例如：users, organizations, settlements')
    action = models.CharField(max_length=255, verbose_name='操作动作', help_text='例如：create_user, update_order_status')
    message = models.TextField(verbose_name='日志信息')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')

    class Meta:
        verbose_name = '系统日志'
        verbose_name_plural = verbose_name
        db_table_comment = "系统操作日志表"
