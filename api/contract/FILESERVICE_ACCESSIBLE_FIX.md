# FileService.accessible 方法不存在的修复

## 🐛 问题描述

在运行合同审查功能时遇到错误：
```
AttributeError("type object 'FileService' has no attribute 'accessible'")
```

## 🔍 问题分析

### 错误原因
在 `api/apps/contract_app.py` 第92行使用了不存在的方法：
```python
if not FileService.accessible(file_id, current_user.id):
```

### 权限检查模式分析
通过分析RAGFlow的代码库，发现：

1. **DocumentService** 有 `accessible` 方法：
   ```python
   @classmethod
   def accessible(cls, doc_id, user_id):
       # 通过join UserTenant表检查权限
   ```

2. **FileService** 没有 `accessible` 方法

3. **文件权限模式**：
   - 文件权限通过 `tenant_id` 字段控制
   - 用户只能访问自己租户（tenant_id = user_id）的文件
   - 在 `file_app.py` 中，文件操作通常只检查文件存在性

## ✅ 修复方案

### 替换权限检查逻辑
将不存在的 `FileService.accessible()` 替换为正确的权限检查：

```python
# 修复前（错误）
if not FileService.accessible(file_id, current_user.id):
    return get_json_result(
        data=False,
        message='No authorization to access this file.',
        code=settings.RetCode.AUTHENTICATION_ERROR
    )

# 修复后（正确）
e, file = FileService.get_by_id(file_id)
if not e:
    return get_data_error_result(message="File not found!")

# 检查文件是否属于当前用户的租户
if file.tenant_id != current_user.id:
    return get_json_result(
        data=False,
        message='No authorization to access this file.',
        code=settings.RetCode.AUTHENTICATION_ERROR
    )
```

### 权限检查逻辑
1. **文件存在性检查**：使用 `FileService.get_by_id()` 检查文件是否存在
2. **权限检查**：比较 `file.tenant_id` 与 `current_user.id`
3. **错误处理**：返回适当的错误消息和状态码

## 🔧 具体修改

### 文件1：`api/apps/contract_app.py`
**位置**：第90-102行

**修改内容**：
- 移除不存在的 `FileService.accessible()` 调用
- 添加正确的文件存在性和权限检查
- 保持相同的错误处理逻辑

### 文件2：`api/apps/contract/utils/document_loader.py`
**位置**：第49-59行

**修改内容**：
- 修复 `load_from_file_id` 方法中的权限检查
- 将 `FileService.accessible()` 替换为正确的实现
- 统一权限检查逻辑

## 🎯 修复效果

### 修复前
- ❌ 运行时抛出 `AttributeError`
- ❌ 合同审查功能无法使用
- ❌ 前端显示服务器错误

### 修复后
- ✅ 正确的权限检查逻辑
- ✅ 合适的错误处理
- ✅ 合同审查功能正常工作
- ✅ 安全性得到保障

## 🔒 安全性考虑

### 权限控制机制
1. **租户隔离**：用户只能访问自己租户的文件
2. **文件存在性**：确保文件存在才进行后续操作
3. **错误消息**：提供清晰的权限错误信息

### 与RAGFlow一致性
- 遵循RAGFlow的权限检查模式
- 使用相同的错误处理方式
- 保持与其他文件操作的一致性

## 🧪 测试验证

### 测试场景
1. **正常访问**：用户访问自己的文件 ✅
2. **权限拒绝**：用户尝试访问其他用户的文件 ✅
3. **文件不存在**：访问不存在的文件ID ✅
4. **错误处理**：各种异常情况的处理 ✅

### 预期行为
- 合法请求正常处理
- 非法请求返回适当的错误码
- 错误消息清晰明确
- 不泄露敏感信息

## 📚 相关代码参考

### DocumentService.accessible 实现
```python
@classmethod
@DB.connection_context()
def accessible(cls, doc_id, user_id):
    docs = cls.model.select(
        cls.model.id).join(
        Knowledgebase, on=(
            Knowledgebase.id == cls.model.kb_id)
    ).join(UserTenant, on=(UserTenant.tenant_id == Knowledgebase.tenant_id)
           ).where(cls.model.id == doc_id, UserTenant.user_id == user_id).paginate(0, 1)
    docs = docs.dicts()
    if not docs:
        return False
    return True
```

### file_app.py 中的权限模式
```python
@manager.route('/get/<file_id>', methods=['GET'])
@login_required
def get(file_id):
    try:
        e, file = FileService.get_by_id(file_id)
        if not e:
            return get_data_error_result(message="Document not found!")
        # 隐式权限控制：用户只能访问自己上传的文件
```

## 🚀 后续优化建议

### 1. 统一权限检查
考虑为 `FileService` 添加 `accessible` 方法，统一权限检查逻辑：
```python
@classmethod
@DB.connection_context()
def accessible(cls, file_id, user_id):
    files = cls.model.select().where(
        cls.model.id == file_id,
        cls.model.tenant_id == user_id
    ).paginate(0, 1)
    return files.count() > 0
```

### 2. 权限装饰器
创建权限检查装饰器，简化代码：
```python
def file_access_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # 权限检查逻辑
        return func(*args, **kwargs)
    return decorated_function
```

### 3. 错误处理标准化
统一文件相关的错误处理和消息格式。

## ✅ 修复完成

- ✅ 移除了不存在的 `FileService.accessible()` 调用
- ✅ 实现了正确的权限检查逻辑
- ✅ 保持了与RAGFlow权限模式的一致性
- ✅ 确保了安全性和功能性

现在合同审查功能应该可以正常工作了！
