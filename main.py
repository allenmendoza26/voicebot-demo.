from fastapi import FastAPI, Request
import uvicorn
import json

app = FastAPI(title="AI Rudder - Payment Reminder Webhook Integration")

payments_database = {
    "CUST-042": {
        "customer_name": "Carlos Rivera",
        "invoice_id": "INV-2026-1045",
        "amount_due": "$3,500 MXN",
        "due_date": "2026-10-15",
        "status": "Pendiente de Cobro",
    }
}


@app.get("/")
def home():
    return {
        "status": "online",
        "system": "AI Rudder Payment Reminder Integration",
    }


@app.post("/webhook/calle-event")
async def handle_calle_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        body_bytes = await request.body()
        payload = {"raw_body": body_bytes.decode("utf-8") or "Petición vacía"}

    # 4.2 MOSTRAR EL PAYLOAD EN TERMINAL
    print("\n==============================================")
    print("[AI RUDDER] Webhook recibido desde CALL-E")
    print("==============================================")
    print("Payload recibido:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    disconnection_reason = payload.get("disconnection_reason") or payload.get("reason") or ""
    call_status = payload.get("call_status") or payload.get("status") or ""
    payment_intent = (payload.get("payment_intent") or payload.get("resolution")
                      or payload.get("payment_commitment_status") or "")
    contact_outcome = payload.get("contact_outcome") or ""

    disconnection_reason = str(disconnection_reason).strip().lower()
    call_status = str(call_status).strip().lower()
    payment_intent = str(payment_intent).strip().lower()
    contact_outcome = str(contact_outcome).strip().lower()

    def normalize_bool(value):
        if isinstance(value, str):
            return value.strip().lower() == "true"
        return bool(value)

    executive_requested = normalize_bool(payload.get("executive_requested", False))
    payment_commitment_confirmed = normalize_bool(payload.get("payment_commitment_confirmed", False))
    human_follow_up_required = normalize_bool(payload.get("human_follow_up_required", False))

    customer_record = payments_database["CUST-042"]

    confirmed_payment_intents = [
        "confirmed",
        "payment_confirmed",
        "payment_commitment",
        "will_pay",
        "committed_to_pay",
        "will_pay_before_deadline",
        "will_pay_after_deadline" ,
        "confirmed_before_deadline"
    ]

    exception_intents = [
        "refused",
        "human_assistance_requested",
        "dispute",
        "uncertain",
        "ambiguous",
        "unknown",
    ]

    exception_contact_outcomes = [
        "no_answer",
        "unreachable",
        "call_rejected",
        "failed",
    ]

    exception_disconnection_reasons = [
        "user_hung_up",
        "call_rejected",
        "timeout",
    ]

    # 8. EVALUAR SI EXISTE UNA EXCEPCIÓN
    is_exception = (
        disconnection_reason in exception_disconnection_reasons
        or call_status == "incomplete"
        or executive_requested is True
        or human_follow_up_required is True
        or payment_intent in exception_intents
        or contact_outcome in exception_contact_outcomes
    )

    is_confirmed_payment = (
        payment_commitment_confirmed is True
        or payment_intent in confirmed_payment_intents
    )

    # 10. GUARDRAIL / SAFE DEFAULT
    if is_exception or not is_confirmed_payment:
        # Actualizamos el registro simulado
        customer_record["status"] = "Escalado a Agente de Cobranza Humana"

        # Intentamos identificar la razón del escalamiento
        reason = disconnection_reason or payment_intent or "unclear_payment_intent"

        print("[GUARDRAIL ACTIVADO]")
        print("No se confirmó compromiso de pago.")
        print(f"Razón / Intención: {reason}")
        print(f"Estado actualizado: {customer_record}")
        print("==============================================\n")

        return {
            "status": "escalated_to_human",
            "reason": reason,
            "payment_commitment_confirmed": False,
            "requires_follow_up": True,
            "message": "No se confirmó un compromiso de pago. El caso fue marcado para seguimiento humano.",
            "customer_data": customer_record,
        }

    # Solo llegamos aquí si no existe ninguna excepción
    customer_record["status"] = "Compromiso de Pago Confirmado"

    print("[ÉXITO]")
    print("Compromiso de pago confirmado por el cliente.")
    print(f"Estado actualizado: {customer_record}")
    print("==============================================\n")

    # Outcome estructurado para el flujo exitoso
    return {
        "status": "success",
        "payment_commitment_confirmed": True,
        "requires_follow_up": False,
        "message": "Compromiso de pago procesado y registrado correctamente.",
        "customer_data": customer_record,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)