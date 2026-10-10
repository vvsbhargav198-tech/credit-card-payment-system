from fastapi import FastAPI

from .routers import payments

DESCRIPTION = """
Payment processing service of the **Credit Card Payment System**.

* Authentication: send the JWT **access** token issued by the Django service
  (`POST http://127.0.0.1:8000/api/auth/login/`) as `Authorization: Bearer <token>`.
* Cards are saved through the Django API. This service only receives a **card id** - never a card number or CVV.
* Payments are simulated: `PENDING` -> `SUCCESS` / `FAILED`.
"""

app = FastAPI(
    title="Credit Card Payment System - Payment Service (FastAPI)",
    description=DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",   
    redoc_url="/redoc",
)

app.include_router(payments.router)


@app.get("/health", tags=["Health"], summary="Liveness probe")
def health():
    return {"status": "ok"}
