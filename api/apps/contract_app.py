import logging
from flask import request
from flask_login import login_required, current_user

from api.db.services.file_service import FileService
from api.utils.api_utils import (
    get_json_result,
    get_data_error_result,
    server_error_response,
    validate_request
)
from api import settings

try:
    from .contract.services.extraction_service import ExtractionService
    from .contract.services.risk_service import RiskService
    from .contract.models.contract_models import Contract
except ImportError:
    import sys
    import os

    contract_path = os.path.join(os.path.dirname(__file__), 'contract')
    if contract_path not in sys.path:
        sys.path.insert(0, contract_path)

    from services.extraction_service import ExtractionService
    from services.risk_service import RiskService
    from models.contract_models import Contract


@manager.route('/extract', methods=['POST'])  # noqa: F821
@login_required
@validate_request("file_id")
def extract_contract():
    """
    Extract key information from contract document.
    ---
    tags:
      - Contract
    security:
      - LoginAuth: []
    parameters:
      - in: body
        name: body
        description: Contract extraction parameters.
        required: true
        schema:
          type: object
          properties:
            file_id:
              type: string
              description: ID of the uploaded contract file.
            extraction_type:
              type: string
              enum: ['basic', 'detailed']
              description: Type of extraction to perform.
    responses:
      200:
        description: Contract extraction successful.
        schema:
          type: object
          properties:
            data:
              type: object
              description: Extracted contract information.
    """
    req = request.json
    file_id = req["file_id"]
    extraction_type = req.get("extraction_type", "basic")

    try:
        e, file = FileService.get_by_id(file_id)
        if not e:
            return get_data_error_result(message="File not found!")
        if file.tenant_id != current_user.id:
            return get_json_result(
                data=False,
                message='No authorization to access this file.',
                code=settings.RetCode.AUTHENTICATION_ERROR
            )

        extraction_service = ExtractionService(current_user.id)
        contract = extraction_service.extract_from_file(file_id, extraction_type)

        if not contract:
            return get_data_error_result(message="Contract extraction failed.")
        return get_json_result(data=contract.model_dump())

    except Exception as e:
        logging.exception(f"Contract extraction failed: {str(e)}")
        return server_error_response(e)


@manager.route('/analyze_risk', methods=['POST'])  
@login_required
@validate_request("contract_data")
def analyze_risk():
    """
    Analyze contract risks.
    ---
    tags:
      - Contract
    security:
      - LoginAuth: []
    parameters:
      - in: body
        name: body
        description: Risk analysis parameters.
        required: true
        schema:
          type: object
          properties:
            contract_data:
              type: object
              description: Contract data object from extraction.
            analysis_type:
              type: string
              enum: ['basic', 'comprehensive']
              description: Type of risk analysis to perform.
    responses:
      200:
        description: Risk analysis completed.
        schema:
          type: object
          properties:
            data:
              type: object
              description: Risk analysis results.
    """
    req = request.json
    contract_data = req["contract_data"]
    analysis_type = req.get("analysis_type", "basic")

    try:
        contract = Contract.model_validate(contract_data)

        risk_service = RiskService(current_user.id)
        risk_analysis = risk_service.analyze_risks(contract, analysis_type)

        if not risk_analysis:
            return get_data_error_result(message="Risk analysis failed.")

        return get_json_result(data=risk_analysis.model_dump())

    except Exception as e:
        logging.exception(f"Risk analysis failed: {str(e)}")
        return server_error_response(e)



