#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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

"""
文档加载器模块，使用智能解析服务
"""
import logging
from typing import Optional

from api.apps.parser_app import IntelligentDocumentParser


class ContractDocumentLoader:
    """合同文档加载器，使用智能解析服务"""

    def __init__(self, user_id: str):
        """
        初始化文档加载器

        Args:
            user_id: 用户ID
        """
        self.user_id = user_id
        # 创建智能解析器，使用自动策略
        self.parser = IntelligentDocumentParser(
            user_id=user_id,
            strategy="auto",
            extract_tables=False,  # 合同审查暂不需要表格提取
            extract_images=False   # 合同审查暂不需要图片提取
        )

    def load_from_file_id(self, file_id: str) -> Optional[str]:
        """
        从文件ID加载文档内容，使用智能解析服务

        Args:
            file_id: RAGFlow文件ID

        Returns:
            Optional[str]: 文档文本内容，如果加载失败则返回None
        """
        try:
            # 使用智能解析器解析文档
            result = self.parser.parse_file(file_id)

            if result is None:
                logging.error(f"Failed to parse document from file {file_id}")
                return None

            # 记录解析信息
            logging.info(f"Successfully parsed file {file_id} using {result['parser_used']} "
                        f"in {result['metadata']['parse_time']}s, "
                        f"content length: {result['metadata']['content_length']}")

            return result["content"]

        except Exception as e:
            logging.exception(f"Failed to load document from file {file_id}: {str(e)}")
            return None

    def get_parse_info(self, file_id: str) -> Optional[dict]:
        """
        获取文档解析信息（不包含内容）

        Args:
            file_id: RAGFlow文件ID

        Returns:
            Optional[dict]: 解析信息，如果失败则返回None
        """
        try:
            result = self.parser.parse_file(file_id)

            if result is None:
                return None

            # 返回不包含内容的元数据
            return {
                "file_id": result["file_id"],
                "file_name": result["file_name"],
                "file_type": result["file_type"],
                "file_size": result["file_size"],
                "parser_used": result["parser_used"],
                "metadata": result["metadata"]
            }

        except Exception as e:
            logging.exception(f"Failed to get parse info for file {file_id}: {str(e)}")
            return None

    def preview_document(self, file_id: str, max_length: int = 500) -> Optional[str]:
        """
        预览文档内容

        Args:
            file_id: RAGFlow文件ID
            max_length: 最大预览长度

        Returns:
            Optional[str]: 预览内容，如果失败则返回None
        """
        try:
            result = self.parser.preview_file(file_id, max_length)

            if result is None:
                return None

            return result["preview_content"]

        except Exception as e:
            logging.exception(f"Failed to preview document {file_id}: {str(e)}")
            return None


