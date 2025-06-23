# 权限系统文档

## 1. 概述

本权限系统为Django应用提供了灵活的权限控制机制，包含两大部分：

*   **页面权限 (RBAC - Role-Based Access Control)**：控制用户是否有权访问某个API端点或执行某个通用操作（例如“查看用户列表”、“创建订单”）。
*   **数据权限**：控制用户能访问哪些特定数据记录或数据范围。这基于一个层级结构：签约公司 -> 集团 -> 企业。用户可以被指定为某个层级的管理员，或被授予对特定企业下特定类型数据的操作权限。

## 2. 页面权限 (RBAC)

### 2.1. 模型

*   `Permission`: 定义一个原子权限。
    *   `name`: 权限的可读名称 (例如："查看用户列表")。
    *   `code`: 程序中用于检查的唯一编码 (例如："view_user_list")。
    *   `url`: (可选) 此权限可能关联的URL模式。
*   `Role`: 代表一个角色，角色可以拥有一组 `Permission`。
    *   `name`: 角色名称 (例如："管理员", "财务人员")。
    *   `permissions`: 多对多关联到 `Permission`。
    *   `users`: 多对多关联到Django内置的 `User` 模型。

### 2.2. 核心API端点 (RBAC)

API均位于 `/api/v1/rbac/` 路径下，且需要管理员权限 (is_staff=True 或 is_superuser=True) 才能访问。

*   `/permissions/`: GET (列表), POST (创建) 页面权限定义。
*   `/permissions/<id>/`: GET (详情), PUT (更新), DELETE (删除) 特定页面权限。
*   `/roles/`: GET (列表), POST (创建) 角色。
*   `/roles/<id>/`: GET (详情), PUT (更新), DELETE (删除) 特定角色。
    *   `/roles/<id>/assign-permissions/` (POST): 为角色分配权限 (请求体: `{"permission_ids": [1, 2]}`)。
    *   `/roles/<id>/get-permissions/` (GET): 获取角色的权限列表。
*   `/users/`: GET (列表), POST (创建) 用户 (基于Django User模型)。
*   `/users/<id>/`: GET (详情), PUT (更新), DELETE (删除) 特定用户。
    *   `/users/<id>/assign-roles/` (POST): 为用户分配角色 (请求体: `{"role_ids": [1, 2]}`)。
    *   `/users/<id>/get-roles/` (GET): 获取用户的角色列表。
*   `/users/current-user-permissions/` (GET): 获取当前登录用户的所拥有全部页面权限编码。
*   `/assign-roles-to-user/` (POST): 批量为用户分配角色 (请求体: `{"user_id": 1, "role_ids": [1,2]}`)。
*   `/assign-permissions-to-role/` (POST): 批量为角色分配权限 (请求体: `{"role_id": 1, "permission_ids": [1,2]}`)。

### 2.3. 在视图中使用 `HasPagePermission`

在DRF的API视图中，通过设置 `permission_classes` 和 `permission_codes` 属性来使用页面权限检查：

```python
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .permissions import HasPagePermission # permissions.permissions.HasPagePermission

class MyProtectedView(APIView):
    permission_classes = [IsAuthenticated, HasPagePermission]
    permission_codes = ['view_dashboard'] # 用户必须拥有 'view_dashboard' 权限

    # 如果需要多个权限中的任何一个即可，可以自定义或扩展 HasPagePermission
    # 如果需要同时拥有多个权限，可以提供一个列表：
    # permission_codes = ['view_dashboard', 'can_export']

    def get(self, request):
        # ... 业务逻辑 ...
        return Response(...)
```

## 3. 数据权限

### 3.1. 模型

*   `Company`: 签约公司。
*   `Group` (permissions.models.Group): 集团，属于一个 `Company`。
*   `Enterprise`: 企业，属于一个 `Group`。
*   `DataPermissionCollection`: 数据权限的类型或集合（由开发人员定义）。
    *   `name`: 可读名称 (例如："业务数据查看", "财务审核")。
    *   `code`: 程序中用于检查的唯一编码 (例如："view_business_data", "finance_audit")。
*   `UserCompanyAdminPermission`: 标记用户是否为某个 `Company` 的管理员。一个用户只能是一个 `Company` 的管理员（通过此表）。
*   `UserGroupAdminPermission`: 标记用户是否为某个 `Group` 的管理员。
*   `UserEnterpriseDataPermission`: 存储用户在特定 `Enterprise` 下拥有的 `DataPermissionCollection` 集合。

### 3.2. 层级和管理员规则

数据权限遵循以下优先规则：

1.  **超级用户 (is_superuser=True)**: 拥有所有数据权限。
2.  **签约公司管理员**: 如果用户是某 `Company` 的管理员 (通过 `UserCompanyAdminPermission` 设置)，则该用户拥有该公司下所有集团、所有企业的全部数据操作权限。此权限具有排他性，设置后不能再配置更细致的集团管理员或企业特定权限。
3.  **集团管理员**: 如果用户是某 `Group` 的管理员 (通过 `UserGroupAdminPermission` 设置)，则该用户拥有该集团下所有企业的全部数据操作权限。此权限也具有排他性（相对于企业特定权限，且不能同时是签约公司管理员）。用户可以管理多个集团。
4.  **企业特定权限**: 如果用户不是签约公司或相关集团的管理员，则权限取决于 `UserEnterpriseDataPermission` 中为该用户和特定企业分配的 `DataPermissionCollection`。

### 3.3. 核心API端点 (数据权限)

API均位于 `/api/v1/rbac/` 路径下 (虽然名为rbac，但也包含了数据权限管理部分)，且需要管理员权限。

*   `/companies/`, `/groups/`, `/enterprises/`: 标准的增删改查API，用于管理组织层级。
*   `/data-permission-collections/`: 增删改查数据权限集合的定义。
*   **`/configure-user-data-permissions/` (POST, GET)**: 这是配置用户数据权限的核心端点。
    *   **POST 请求体示例**:
        ```json
        {
            "user_id": 1,
            "is_company_admin": false, // true 则 company_id 必填，且下面两项必须为空
            "company_id": null,      // 如果 is_company_admin 为 true, 提供签约公司ID
            "group_admin_for": [1, 2], // 用户作为管理员的集团ID列表
            "enterprise_permissions": [ // 用户在特定企业的具体权限集合
                {
                    "enterprise_id": 3,
                    "permission_codes": ["view_business_data", "perform_refund"]
                },
                {
                    "enterprise_id": 4,
                    "permission_codes": ["view_business_data"]
                }
            ]
        }
        ```
    *   **GET 请求参数**: `?user_id=<id>`，返回该用户当前的数据权限配置结构。
    *   **重要**: 此接口的POST操作会首先清除用户所有现存的数据权限（公司管理员、集团管理员、企业特定权限），然后根据请求体中的内容重新建立。

*   `/check-data-permission/` (GET): 一个辅助测试端点。
    *   参数: `?user_id=<id>&enterprise_id=<id>&permission_codes=code1,code2`
    *   返回用户是否对该企业拥有所有指定的 `permission_codes`。

### 3.4. `has_data_permission` 函数

后端逻辑中使用 `permissions.views.has_data_permission(user, enterprise_id, required_permission_codes)` 函数来检查用户的数据权限。
*   `user`: Django User 对象。
*   `enterprise_id`: 目标企业的ID。
*   `required_permission_codes`: 一个字符串列表，包含用户必须拥有的所有数据权限集合编码。

## 4. API权限检查示例 (组合使用)

参考 `EnterpriseOrdersView` (`permissions/views.py`):

```python
from .permissions import HasPagePermission
from .views import has_data_permission # Note: has_data_permission is in views.py

class EnterpriseOrdersView(APIView):
    permission_classes = [IsAuthenticated, HasPagePermission]
    permission_codes = ['view_orders'] # 1. 页面权限检查

    def get(self, request, enterprise_id, *args, **kwargs):
        # ... (获取 enterprise 对象) ...

        required_data_perm_codes = ["view_business_data"]

        # 2. 数据权限检查
        if not has_data_permission(request.user, enterprise_id, required_data_perm_codes):
            return Response({"error": "Data permission denied."}, status=status.HTTP_403_FORBIDDEN)

        # ... (业务逻辑) ...
        return Response(data)
```

## 5. 设置和配置步骤

1.  **定义页面权限**:
    *   通过 `/api/v1/rbac/permissions/` POST接口创建 `Permission` 对象，例如：
        `{"name": "查看订单", "code": "view_orders"}`
2.  **定义数据权限集合**:
    *   通过 `/api/v1/rbac/data-permission-collections/` POST接口创建 `DataPermissionCollection` 对象，例如：
        `{"name": "业务数据查看", "code": "view_business_data", "description": "允许查看企业业务相关数据"}`
        `{"name": "退款操作", "code": "perform_refund"}`
3.  **创建角色并分配页面权限**:
    *   通过 `/api/v1/rbac/roles/` POST接口创建 `Role`，例如 `{"name": "业务员"}`。
    *   通过 `/api/v1/rbac/roles/<role_id>/assign-permissions/` POST接口为角色分配页面权限。
4.  **为用户分配角色**:
    *   通过 `/api/v1/rbac/users/<user_id>/assign-roles/` POST接口为用户分配角色。
5.  **配置用户的数据权限**:
    *   使用 `/api/v1/rbac/configure-user-data-permissions/` POST接口。根据需求，将用户设置为：
        *   签约公司管理员 (设置 `is_company_admin: true` 和 `company_id`)。
        *   或，集团管理员 (在 `group_admin_for` 列表中提供集团ID)。
        *   或，授予特定企业的特定数据权限集合 (填充 `enterprise_permissions` 列表)。
        *   记住这些配置之间的排他性规则。

通过以上步骤，可以为用户精确配置其操作权限和数据访问范围。
```
