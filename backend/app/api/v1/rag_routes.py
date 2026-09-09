from fastapi import APIRouter, HTTPException, status
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput, RAGEvidenceOutput

router = APIRouter(prefix="/rag", tags=["Agricultural RAG Knowledge"])

@router.post("/search", response_model=RAGEvidenceOutput)
async def search_agricultural_evidence(query_in: RAGQueryInput):
    """
    Search verified ICAR, State Agricultural University, and official extension research documents.
    """
    try:
        return AgriculturalRAGService.search(query_in)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/debug")
async def debug_agricultural_evidence(query_in: RAGQueryInput):
    """
    Step 25 RAG Debug Mode: Inspect request, query rewrites, candidates, ranking scores, accepted/rejected evidence, and LLM context.
    """
    try:
        return AgriculturalRAGService.search_debug(query_in)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

