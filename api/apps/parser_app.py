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
智能文档解析服务
提供统一的文档解析API和智能解析器，支持多种文件格式的智能解析
"""

import logging
import time
from typing import Optional, Dict, List, Any
from pathlib import Path
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from api.utils.api_utils import get_json_result, server_error_response, get_data_error_result, validate_request
from api.db.services.file_service import FileService
from deepdoc.parser import DocxParser, ExcelParser, HtmlParser, TxtParser, PlainParser, PdfParser
from rag.utils.storage_factory import STORAGE_IMPL

# Flask Blueprint
manager = Blueprint("parser_app", __name__, url_prefix="/v1/parser")


class IntelligentDocumentParser:
    """智能文档解析器"""
    
    # 支持的文件格式
    SUPPORTED_FORMATS = {
        '.pdf': 'PDF文档',
        '.docx': 'Word文档',
        '.doc': 'Word文档',
        '.xlsx': 'Excel表格',
        '.xls': 'Excel表格',
        '.txt': '文本文件',
        '.html': 'HTML文件',
        '.htm': 'HTML文件'
    }
    
    # 解析策略
    STRATEGIES = {
        'auto': '自动选择最优策略',
        'fast': '快速解析（优先速度）',
        'accurate': '精确解析（优先准确性）',
        'comprehensive': '全面解析（包含表格、图片等）'
    }
    
    def __init__(self, user_id: str, strategy: str = "auto", 
                 extract_tables: bool = False, extract_images: bool = False):
        """
        初始化智能文档解析器
        
        Args:
            user_id: 用户ID
            strategy: 解析策略
            extract_tables: 是否提取表格
            extract_images: 是否提取图片描述
        """
        self.user_id = user_id
        self.strategy = strategy
        self.extract_tables = extract_tables
        self.extract_images = extract_images
        
        # 验证策略
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Unsupported strategy: {strategy}")
    
    def parse_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        解析单个文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            Optional[Dict]: 解析结果，失败时返回None
        """
        try:
            start_time = time.time()
            
            # 获取文件信息
            e, file_info = FileService.get_by_id(file_id)
            if not e:
                logging.error(f"File {file_id} not found")
                return None
            
            # 检查权限
            if file_info.tenant_id != self.user_id:
                logging.error(f"User {self.user_id} has no access to file {file_id}")
                return None
            
            # 检查文件格式
            file_extension = Path(file_info.name).suffix.lower()
            if file_extension not in self.SUPPORTED_FORMATS:
                logging.error(f"Unsupported file format: {file_extension}")
                return None
            
            # 获取文件内容
            file_binary = self._get_file_binary(file_info)
            if file_binary is None:
                logging.error(f"Failed to read file content for {file_id}")
                return None
            
            # 执行解析
            parse_result = self._parse_content(file_info.name, file_extension, file_binary)
            
            # 构建返回结果
            result = {
                "file_id": file_id,
                "file_name": file_info.name,
                "file_type": file_extension,
                "file_size": file_info.size,
                "parser_used": parse_result.get("parser_used", "unknown"),
                "content": parse_result.get("content", ""),
                "metadata": {
                    "parse_time": round(time.time() - start_time, 2),
                    "content_length": len(parse_result.get("content", "")),
                    "word_count": len(parse_result.get("content", "").split()),
                    "strategy_used": self.strategy,
                    "pdf_type": parse_result.get("pdf_type"),  # 仅PDF有此字段
                },
                "tables": parse_result.get("tables", []) if self.extract_tables else [],
                "images": parse_result.get("images", []) if self.extract_images else []
            }
            
            logging.info(f"Successfully parsed file {file_id} ({file_info.name}) in {result['metadata']['parse_time']}s")
            return result
            
        except Exception as e:
            logging.exception(f"Failed to parse file {file_id}: {str(e)}")
            return None
    
    def parse_files_batch(self, file_ids: List[str]) -> Dict[str, List]:
        """批量解析文件"""
        results = {"success": [], "failed": []}
        
        for file_id in file_ids:
            try:
                result = self.parse_file(file_id)
                if result:
                    results["success"].append(result)
                else:
                    results["failed"].append({"file_id": file_id, "error": "Parse failed"})
            except Exception as e:
                results["failed"].append({"file_id": file_id, "error": str(e)})
        
        return results
    
    def preview_file(self, file_id: str, max_length: int = 1000) -> Optional[Dict[str, Any]]:
        """预览文件内容"""
        try:
            original_strategy = self.strategy
            self.strategy = "fast"
            
            result = self.parse_file(file_id)
            self.strategy = original_strategy
            
            if result is None:
                return None
            
            content = result["content"]
            preview_content = content[:max_length] if len(content) > max_length else content
            
            return {
                "file_id": file_id,
                "file_name": result["file_name"],
                "file_type": result["file_type"],
                "preview_content": preview_content,
                "total_length": len(content),
                "is_truncated": len(content) > max_length,
                "parser_used": result["parser_used"]
            }
            
        except Exception as e:
            logging.exception(f"Failed to preview file {file_id}: {str(e)}")
            return None
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """获取支持的文件格式信息"""
        return {
            "formats": self.SUPPORTED_FORMATS,
            "strategies": self.STRATEGIES,
            "features": {
                "extract_tables": "支持表格提取",
                "extract_images": "支持图片描述提取",
                "batch_processing": "支持批量处理",
                "intelligent_pdf": "智能PDF类型检测"
            }
        }
    
    def _get_file_binary(self, file_info) -> Optional[bytes]:
        """获取文件二进制内容"""
        try:
            return STORAGE_IMPL.get(file_info.parent_id, file_info.location)
        except Exception as e:
            logging.exception(f"Failed to get file binary: {str(e)}")
            return None

    def _parse_content(self, filename: str, file_extension: str, file_binary: bytes) -> Dict[str, Any]:
        """根据文件类型和策略解析内容"""
        try:
            if file_extension == '.pdf':
                return self._parse_pdf_intelligent(filename, file_binary)
            elif file_extension in ['.docx', '.doc']:
                return self._parse_docx(filename, file_binary)
            elif file_extension in ['.xlsx', '.xls']:
                return self._parse_excel(filename, file_binary)
            elif file_extension == '.txt':
                return self._parse_txt(filename, file_binary)
            elif file_extension in ['.html', '.htm']:
                return self._parse_html(filename, file_binary)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
        except Exception as e:
            logging.exception(f"Failed to parse content: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_pdf_intelligent(self, filename: str, file_binary: bytes) -> Dict[str, Any]:
        """智能解析PDF文件"""
        try:
            if self.strategy == "fast":
                return self._parse_pdf_fast(filename, file_binary)
            elif self.strategy == "accurate":
                return self._parse_pdf_accurate(filename, file_binary)
            elif self.strategy == "comprehensive":
                return self._parse_pdf_comprehensive(filename, file_binary)
            else:  # auto
                return self._parse_pdf_auto(filename, file_binary)
        except Exception as e:
            logging.exception(f"Failed to parse PDF intelligently: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_pdf_auto(self, filename: str, file_binary: bytes) -> Dict[str, Any]:
        """自动策略解析PDF"""
        try:
            # 检测PDF类型
            pdf_type = self._detect_pdf_type(file_binary)

            if pdf_type == "text_based":
                return self._parse_pdf_with_plain_parser(filename, file_binary, pdf_type)
            elif pdf_type == "mixed":
                return self._parse_pdf_with_fallback(filename, file_binary, pdf_type)
            else:  # image_based
                return self._parse_pdf_with_ocr(filename, file_binary, pdf_type)
        except Exception as e:
            logging.exception(f"Auto PDF parsing failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_pdf_fast(self, filename: str, file_binary: bytes) -> Dict[str, Any]:
        """快速策略解析PDF"""
        try:
            return self._parse_pdf_with_plain_parser(filename, file_binary, "fast_mode")
        except Exception as e:
            logging.exception(f"Fast PDF parsing failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_pdf_accurate(self, filename: str, file_binary: bytes) -> Dict[str, Any]:
        """精确策略解析PDF"""
        try:
            return self._parse_pdf_with_ocr(filename, file_binary, "accurate_mode")
        except Exception as e:
            logging.exception(f"Accurate PDF parsing failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_pdf_comprehensive(self, filename: str, file_binary: bytes) -> Dict[str, Any]:
        """全面策略解析PDF"""
        try:
            result = self._parse_pdf_with_ocr(filename, file_binary, "comprehensive_mode")

            if self.extract_tables:
                result["tables"] = self._extract_tables_from_pdf(file_binary)

            if self.extract_images:
                result["images"] = self._extract_images_from_pdf(file_binary)

            return result
        except Exception as e:
            logging.exception(f"Comprehensive PDF parsing failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _detect_pdf_type(self, file_binary: bytes) -> str:
        """检测PDF类型"""
        try:
            plain_parser = PlainParser()
            sections, _ = plain_parser(file_binary)
            text_content = '\n'.join([section[0] for section in sections if section[0].strip()])

            text_length = len(text_content.strip())
            word_count = len(text_content.split())

            if text_length >= 500 and word_count >= 50:
                return "text_based"
            elif text_length >= 100 and word_count >= 10:
                return "mixed"
            else:
                return "image_based"
        except Exception as e:
            logging.warning(f"PDF type detection failed: {str(e)}, defaulting to mixed")
            return "mixed"

    def _parse_pdf_with_plain_parser(self, filename: str, file_binary: bytes, pdf_type: str) -> Dict[str, Any]:
        """使用PlainParser解析PDF"""
        try:
            plain_parser = PlainParser()
            sections, _ = plain_parser(file_binary)
            content = '\n'.join([section[0] for section in sections if section[0].strip()])

            return {
                "content": content,
                "parser_used": "PlainParser",
                "pdf_type": pdf_type
            }
        except Exception as e:
            logging.exception(f"PlainParser failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_pdf_with_ocr(self, filename: str, file_binary: bytes, pdf_type: str) -> Dict[str, Any]:
        """使用OCR解析PDF"""
        try:
            ocr_parser = PdfParser()
            sections, _ = ocr_parser(file_binary)
            content = '\n'.join([section[0] for section in sections if section[0].strip()])

            return {
                "content": content,
                "parser_used": "OCR_Parser",
                "pdf_type": pdf_type
            }
        except Exception as e:
            logging.exception(f"OCR parser failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_pdf_with_fallback(self, filename: str, file_binary: bytes, pdf_type: str) -> Dict[str, Any]:
        """使用回退策略解析PDF"""
        try:
            # 先尝试PlainParser
            plain_result = self._parse_pdf_with_plain_parser(filename, file_binary, pdf_type)

            # 如果结果不够好，使用OCR
            if len(plain_result["content"].strip()) < 200:
                ocr_result = self._parse_pdf_with_ocr(filename, file_binary, pdf_type)

                if len(ocr_result["content"].strip()) > len(plain_result["content"].strip()):
                    ocr_result["parser_used"] = "OCR_Parser_Fallback"
                    return ocr_result

            plain_result["parser_used"] = "PlainParser_Primary"
            return plain_result
        except Exception as e:
            logging.exception(f"Fallback parsing failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_docx(self, filename: str, file_binary: bytes) -> Dict[str, Any]:
        """解析Word文档"""
        try:
            docx_parser = DocxParser()
            sections, tables = docx_parser(file_binary)

            text_parts = [section[0] for section in sections if section[0].strip()]
            table_data = []

            if self.extract_tables and tables:
                for table in tables:
                    if isinstance(table, list):
                        table_data.extend(table)
                        text_parts.extend(table)
                    else:
                        table_data.append(str(table))
                        text_parts.append(str(table))

            result = {"content": '\n'.join(text_parts), "parser_used": "DocxParser"}
            if self.extract_tables:
                result["tables"] = table_data
            return result
        except Exception as e:
            logging.exception(f"DOCX parsing failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_excel(self, filename: str, file_binary: bytes) -> Dict[str, Any]:
        """解析Excel文件"""
        try:
            excel_parser = ExcelParser()
            sections = excel_parser(file_binary)

            text_parts = []
            table_data = []

            for section in sections:
                content = str(section[0]) if isinstance(section, (list, tuple)) and len(section) > 0 else str(section)
                text_parts.append(content)
                if self.extract_tables:
                    table_data.append(content)

            result = {"content": '\n'.join(text_parts), "parser_used": "ExcelParser"}
            if self.extract_tables:
                result["tables"] = table_data
            return result
        except Exception as e:
            logging.exception(f"Excel parsing failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_txt(self, filename: str, file_binary: bytes) -> Dict[str, Any]:
        """解析文本文件"""
        try:
            txt_parser = TxtParser()
            sections = txt_parser(filename, file_binary)

            text_parts = [section[0] for section in sections if section[0].strip()]
            return {"content": '\n'.join(text_parts), "parser_used": "TxtParser"}
        except Exception as e:
            logging.exception(f"TXT parsing failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _parse_html(self, filename: str, file_binary: bytes) -> Dict[str, Any]:
        """解析HTML文件"""
        try:
            html_parser = HtmlParser()
            sections = html_parser(filename, file_binary)

            text_parts = [section for section in sections if section.strip()]
            return {"content": '\n'.join(text_parts), "parser_used": "HtmlParser"}
        except Exception as e:
            logging.exception(f"HTML parsing failed: {str(e)}")
            return {"content": "", "parser_used": "failed"}

    def _extract_tables_from_pdf(self, file_binary: bytes) -> List[str]:
        """从PDF中提取表格（占位符方法）"""
        # TODO: 实现PDF表格提取逻辑
        return []

    def _extract_images_from_pdf(self, file_binary: bytes) -> List[str]:
        """从PDF中提取图片描述（占位符方法）"""
        # TODO: 实现PDF图片提取和描述逻辑
        return []


# ==================== API 端点 ====================

@manager.route('/parse', methods=['POST'])
@login_required
@validate_request("file_id")
def parse_document():
    """智能解析文档"""
    try:
        req = request.json
        file_id = req["file_id"]
        parser_strategy = req.get("parser_strategy", "auto")
        extract_tables = req.get("extract_tables", False)
        extract_images = req.get("extract_images", False)

        # 验证文件权限
        e, file_info = FileService.get_by_id(file_id)
        if not e:
            return get_data_error_result(message=f"File {file_id} not found")

        if file_info.tenant_id != current_user.id:
            return get_data_error_result(message="Access denied: file does not belong to current user")

        # 创建智能解析器
        parser = IntelligentDocumentParser(
            user_id=current_user.id,
            strategy=parser_strategy,
            extract_tables=extract_tables,
            extract_images=extract_images
        )

        # 执行解析
        result = parser.parse_file(file_id)

        if result is None:
            return get_data_error_result(message="Failed to parse document")

        return get_json_result(data=result)

    except Exception as e:
        logging.exception(f"Document parsing failed: {str(e)}")
        return server_error_response(e)


@manager.route('/parse/batch', methods=['POST'])
@login_required
@validate_request("file_ids")
def parse_documents_batch():
    """批量解析文档"""
    try:
        req = request.json
        file_ids = req["file_ids"]
        parser_strategy = req.get("parser_strategy", "auto")
        extract_tables = req.get("extract_tables", False)
        extract_images = req.get("extract_images", False)

        if not isinstance(file_ids, list) or len(file_ids) == 0:
            return get_data_error_result(message="file_ids must be a non-empty list")

        if len(file_ids) > 50:
            return get_data_error_result(message="Maximum 50 files allowed per batch")

        # 创建智能解析器
        parser = IntelligentDocumentParser(
            user_id=current_user.id,
            strategy=parser_strategy,
            extract_tables=extract_tables,
            extract_images=extract_images
        )

        # 批量解析
        results = parser.parse_files_batch(file_ids)

        return get_json_result(data=results)

    except Exception as e:
        logging.exception(f"Batch document parsing failed: {str(e)}")
        return server_error_response(e)


@manager.route('/supported-formats', methods=['GET'])
@login_required
def get_supported_formats():
    """获取支持的文件格式列表"""
    try:
        parser = IntelligentDocumentParser(user_id=current_user.id)
        formats_info = parser.get_supported_formats()

        return get_json_result(data=formats_info)

    except Exception as e:
        logging.exception(f"Failed to get supported formats: {str(e)}")
        return server_error_response(e)


@manager.route('/parse/preview', methods=['POST'])
@login_required
@validate_request("file_id")
def preview_document():
    """预览文档解析结果"""
    try:
        req = request.json
        file_id = req["file_id"]
        parser_strategy = req.get("parser_strategy", "fast")
        max_length = req.get("max_length", 1000)

        # 验证文件权限
        e, file_info = FileService.get_by_id(file_id)
        if not e:
            return get_data_error_result(message=f"File {file_id} not found")

        if file_info.tenant_id != current_user.id:
            return get_data_error_result(message="Access denied")

        # 创建解析器并预览
        parser = IntelligentDocumentParser(
            user_id=current_user.id,
            strategy=parser_strategy
        )

        preview_result = parser.preview_file(file_id, max_length=max_length)

        if preview_result is None:
            return get_data_error_result(message="Failed to preview document")

        return get_json_result(data=preview_result)

    except Exception as e:
        logging.exception(f"Document preview failed: {str(e)}")
        return server_error_response(e)
