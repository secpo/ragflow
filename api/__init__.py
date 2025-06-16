#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

# 支持在开发/测试环境中禁用beartype
import os
DISABLE_BEARTYPE = os.environ.get('DISABLE_BEARTYPE', '').lower() in ('1', 'true', 'yes')

if not DISABLE_BEARTYPE:
    try:
        from beartype.claw import beartype_this_package
        beartype_this_package()
    except ImportError:
        # beartype不可用时跳过类型检查，但发出警告
        import warnings
        warnings.warn("beartype not available, skipping runtime type checking", ImportWarning)
