from fastapi import APIRouter

router = APIRouter()

@router.post("/generate-question")
async def generate_question():
    """Placeholder endpoint for generating interview questions."""
    pass
