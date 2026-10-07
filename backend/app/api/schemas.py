from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Mode = Literal["demo", "anthropic"]


class HealthTools(BaseModel):
    sandbox: bool
    mcp: bool


class HealthFeatures(BaseModel):
    customer_management: Literal[True] = True
    document_reading: Literal[True] = True


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mode: Mode
    model: str
    embedding: str
    tools: HealthTools
    features: HealthFeatures = Field(default_factory=HealthFeatures)


class CompanyInfo(BaseModel):
    company_name: str
    company_description: str
    assistant_name: str
    website: str | None = None
    suggested_questions: list[str] | None = None


class Document(BaseModel):
    id: str
    name: str
    chunks: int
    characters: int
    created_at: str


class DocumentDetail(Document):
    content: str
    reconstructed: bool


class Source(BaseModel):
    document_id: str
    document_name: str
    chunk_id: str
    text: str
    score: float


class DocumentList(BaseModel):
    documents: list[Document]
    total_chunks: int


class UploadResponse(DocumentList):
    skipped: list[str]


class ToolTrace(BaseModel):
    id: str
    tool: str
    input: dict[str, Any]
    output: str
    status: Literal["completed", "error"]
    duration_ms: int


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=30000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=40)
    session_id: str | None = Field(default=None, max_length=100, pattern=r"^[\w-]+$")

    @model_validator(mode="after")
    def bounded_history(self) -> "ChatRequest":
        if sum(len(item.content) for item in self.history) > 32000:
            raise ValueError("El historial excede los 32000 caracteres permitidos.")
        return self


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    trace: list[ToolTrace]
    mode: Mode
    model: str
    usage: Usage
    session_id: str


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=60)
    input: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False


class ActionConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["create_demo_request", "create_support_ticket"]
    input: dict[str, Any]
    action_key: str = Field(pattern=r"^[a-fA-F0-9-]{36}$")
