import uuid

from pydantic import BaseModel

from app.schemas.generated_content import GeneratedQuizQuestion, QuizQuestionContent


class QuizQuestionOut(BaseModel):
    id: uuid.UUID
    training_id: uuid.UUID
    question_json: GeneratedQuizQuestion

    model_config = {"from_attributes": True}


class QuizQuestionWrite(BaseModel):
    question_json: QuizQuestionContent


class QuizQuestionUpdate(BaseModel):
    question_json: QuizQuestionContent


class QuizSubmission(BaseModel):
    answers: list[dict]
