from pydantic import BaseModel, Field

class ApprovalInput(BaseModel):
    approval_no: str
    applicant: str = ""
    department: str = ""
    buyer_name: str
    payee_name: str
    amount: float = Field(gt=0)
    tax_rate: float | None = None
    expense_subject: str = ""
    business_reason: str = ""
    contract_summary: str = ""
