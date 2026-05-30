from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from uuid import uuid4
from datetime import UTC, datetime
from typing import Any

from .agents import AGENTS, RENOVATION_AGENTS, TRIAGE_ROUTER_AGENT
from .io_utils import append_jsonl, write_json
from .llm import ChatModel
from .models import RunState, AgentStep
from .report import write_markdown_report
from .tools import (
    calculate_tile_boxes,
    calculate_paint_liters,
    calculate_total,
    determine_budget_status,
    verify_quote_risks,
)
from .storage import (
    DEFAULT_DB_PATH,
    ProductRepository,
    InventoryRepository,
    TicketRepository,
    QuoteRepository,
    AgentTraceRepository,
    get_connection,
)


def normalize_triage_output(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}

    # 1. Normalize selected_pipeline
    selected = str(raw.get("selected_pipeline", "")).strip().lower()
    if selected in ["renovation_quote", "renovation", "quote", "quotation"]:
        normalized_pipeline = "renovation_quote"
    else:
        normalized_pipeline = "support"

    # 2. Normalize secondary_intents
    sec = raw.get("secondary_intents", [])
    if isinstance(sec, list):
        secondary_intents = [str(x) for x in sec]
    elif isinstance(sec, str):
        secondary_intents = [sec] if sec.strip() else []
    else:
        secondary_intents = []

    # 3. Normalize multi_intent
    multi = raw.get("multi_intent")
    if isinstance(multi, bool):
        multi_intent = multi
    elif isinstance(multi, str):
        multi_intent = multi.strip().lower() in ["true", "1", "yes", "ya"]
    elif isinstance(multi, (int, float)):
        multi_intent = bool(multi)
    else:
        multi_intent = False

    # 4. Normalize other string fields
    primary_intent = str(raw.get("primary_intent", "")).strip() or "general_support"
    routing_reason = str(raw.get("routing_reason", "")).strip() or "Layanan pelanggan QHome Mart standar."
    priority_rule = str(raw.get("priority_rule", "")).strip() or "standard_routing"
    staff_handoff_notes = str(raw.get("staff_handoff_notes", "")).strip() or "Tangani pertanyaan umum dari pelanggan secara profesional."

    customer_whatsapp = raw.get("customer_whatsapp")
    if customer_whatsapp:
        customer_whatsapp = str(customer_whatsapp).strip()
    else:
        customer_whatsapp = None

    customer_name = raw.get("customer_name")
    if customer_name:
        customer_name = str(customer_name).strip()
    else:
        customer_name = None

    return {
        "primary_intent": primary_intent,
        "secondary_intents": secondary_intents,
        "selected_pipeline": normalized_pipeline,
        "multi_intent": multi_intent,
        "routing_reason": routing_reason,
        "priority_rule": priority_rule,
        "staff_handoff_notes": staff_handoff_notes,
        "customer_whatsapp": customer_whatsapp,
        "customer_name": customer_name,
    }


def is_coding_request(text: str) -> bool:
    lowered = text.lower()
    coding_terms = [
        "coding",
        "kode",
        "script",
        "javascript",
        "python",
        "php",
        "laravel",
        "react",
        "bot",
        "scraping",
        "auto checkout",
        "program",
        "debug",
    ]
    request_terms = ["buatkan", "bikinkan", "tolong", "ajarin", "bantu", "generate"]
    return any(term in lowered for term in coding_terms) and any(term in lowered for term in request_terms)


def apply_scope_guard(ticket: dict[str, Any], triage_output: dict[str, Any]) -> dict[str, Any]:
    latest = str(ticket.get("message", ""))
    if not is_coding_request(latest):
        return triage_output

    guarded = dict(triage_output)
    guarded["primary_intent"] = "out_of_scope_coding"
    guarded["secondary_intents"] = []
    guarded["selected_pipeline"] = "support"
    guarded["multi_intent"] = False
    guarded["priority_rule"] = "out_of_scope_guard"
    guarded["routing_reason"] = (
        "Pesan terbaru meminta bantuan coding atau otomasi yang berada di luar layanan QHome Mart."
    )
    guarded["staff_handoff_notes"] = (
        "Tolak permintaan coding secara sopan. Arahkan pelanggan kembali ke bantuan produk, pesanan, pengiriman, renovasi, atau komplain QHome Mart."
    )
    return guarded


def apply_latest_message_routing(ticket: dict[str, Any], triage_output: dict[str, Any]) -> dict[str, Any]:
    latest = str(ticket.get("message", "")).lower()
    history = str(ticket.get("history", "")).strip()
    if not history or not latest:
        return triage_output

    material_terms = ["batu bata", "semen", "besi", "pasir", "keramik", "cat"]
    order_terms = ["memesan", "pesan", "mau beli", "ingin beli", "order", "total harga", "berapa total", "kapan", "datangnya"]
    renovation_terms = ["renovasi", "estimasi", "budget", "butuh apa", "kira kira butuh", "kamar saya", "ruangan"]

    previous_material_order = find_latest_material_order_message(history)
    latest_damage_concern = (
        any(word in latest for word in ["pecah", "rusak", "retak"])
        and any(term in latest for term in ["jangan sampai", "jgn sampai", "agar tidak", "biar tidak", "semoga tidak", "saat tiba"])
        and bool(previous_material_order)
    )
    latest_has_complaint = any(
        word in latest
        for word in ["pecah", "rusak", "retak", "komplain", "refund", "retur", "belum sampai", "terlambat"]
    )
    if latest_has_complaint and not latest_damage_concern:
        return triage_output

    latest_material_order = any(term in latest for term in material_terms) and (
        any(term in latest for term in order_terms) or bool(re.search(r"\b\d+\s*(pcs|buah|sak|pack|batang|m3)\b", latest))
    )
    latest_renovation = any(term in latest for term in renovation_terms)
    if latest_damage_concern:
        latest_material_order = True
    if not latest_material_order and not latest_renovation:
        return triage_output

    routed = dict(triage_output)
    previous_intent = str(routed.get("primary_intent") or "").strip()
    secondary = list(routed.get("secondary_intents") or [])
    if previous_intent and previous_intent not in {"renovation_quote", "material_order", "general_support"}:
        secondary.append(previous_intent)
    if "damaged_item" in str(ticket.get("history", "")).lower() or any(word in str(ticket.get("history", "")).lower() for word in ["pecah", "rusak", "retak"]):
        secondary.append("damaged_item")

    routed["primary_intent"] = "material_order" if latest_material_order else "renovation_quote"
    routed["secondary_intents"] = sorted(set(item for item in secondary if item))
    routed["selected_pipeline"] = "renovation_quote"
    routed["multi_intent"] = bool(routed["secondary_intents"])
    routed["priority_rule"] = "dynamic_pipeline_switch"
    if latest_damage_concern:
        routed["active_request_message"] = f"{previous_material_order}\nCustomer concern: {ticket.get('message', '')}"
        routed["delivery_quality_concern"] = True
    else:
        routed["active_request_message"] = ticket.get("message", "")
    routed["routing_reason"] = (
        "Pesan terbaru pelanggan berisi permintaan baru sehingga pipeline dialihkan ke quotation/material planning. "
        "Riwayat komplain sebelumnya tetap disimpan sebagai konteks handoff staf."
    )
    routed["staff_handoff_notes"] = (
        "Pipeline dipindahkan berdasarkan pesan terbaru. Tetap catat isu sebelumnya dari riwayat percakapan, "
        "tetapi respons aktif harus menjawab permintaan terbaru pelanggan."
    )
    return routed


def find_latest_material_order_message(history: str) -> str:
    material_terms = ["batu bata", "semen", "besi", "pasir", "keramik", "cat"]
    order_terms = ["memesan", "pesan", "mau beli", "ingin beli", "order", "total harga", "berapa total"]
    candidates = []
    for line in history.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if lowered.startswith("customer:"):
            stripped = stripped.split(":", 1)[1].strip()
            lowered = stripped.lower()
        elif lowered.startswith("assistant:"):
            continue
        if any(term in lowered for term in material_terms) and (
            any(term in lowered for term in order_terms)
            or bool(re.search(r"\b\d+\s*(pcs|buah|sak|pack|batang|m3)\b", lowered))
        ):
            candidates.append(stripped)
    return candidates[-1] if candidates else ""


def build_pipeline_ticket(ticket: dict[str, Any], triage_output: dict[str, Any]) -> dict[str, Any]:
    """Use the latest customer request as the active task after a deliberate pipeline switch."""
    if triage_output.get("priority_rule") not in {"dynamic_pipeline_switch", "out_of_scope_guard"}:
        return ticket

    active_ticket = dict(ticket)
    active_ticket["history_context"] = ticket.get("history", "")
    active_ticket["original_message"] = ticket.get("message", "")
    active_ticket["message"] = triage_output.get("active_request_message") or ticket.get("message", "")
    active_ticket["history"] = ""
    if triage_output.get("customer_whatsapp"):
        active_ticket["customer_whatsapp"] = triage_output.get("customer_whatsapp")
    if triage_output.get("customer_name"):
        active_ticket["customer_name"] = triage_output.get("customer_name")
    return active_ticket


def run_workflow(
    *,
    model: ChatModel,
    ticket: dict,
    knowledge_base: dict,
    output_dir: Path,
    run_id: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
    session_id: str | None = None,
    session_store: Any = None,
) -> dict:
    actual_run_id = run_id or f"run-{uuid4().hex[:8]}"
    run_dir = output_dir / actual_run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Initialize SQLite repositories
    prod_repo = ProductRepository(db_path)
    inv_repo = InventoryRepository(db_path)
    tkt_repo = TicketRepository(db_path)
    qte_repo = QuoteRepository(db_path)
    trace_repo = AgentTraceRepository(db_path)

    # Create Ticket code
    ticket_code = ticket.get("ticket_code") or f"TKT-{actual_run_id[4:9].upper()}"
    session_id = ticket.get("session_id") or f"sess-{actual_run_id}"
    customer_name = ticket.get("customer_name") or "Pelanggan"

    # Save to agent_runs table
    trace_repo.create_run(actual_run_id, ticket_code, "live" if hasattr(model, "settings") else "mock")

    # Load state
    state = RunState(run_id=actual_run_id, ticket=ticket, knowledge_base=knowledge_base)

    # Initialize the real-time agent trace list
    trace_steps = []

    # Run formal triage agent using LLM (or mock model)
    triage_payload = {"ticket": ticket}
    triage_raw, triage_dur = timed_agent_run(TRIAGE_ROUTER_AGENT, model, state, triage_payload)
    triage_output = normalize_triage_output(triage_raw)
    triage_output = apply_scope_guard(ticket, triage_output)
    triage_output = apply_latest_message_routing(ticket, triage_output)

    state.add_step(TRIAGE_ROUTER_AGENT.name, triage_output)

    # Save step to SQLite trace_repo
    trace_repo.add_step(actual_run_id, TRIAGE_ROUTER_AGENT.name, triage_payload, triage_output)

    # Log step to file
    append_jsonl(
        run_dir / "interactions.jsonl",
        {
            "run_id": actual_run_id,
            "agent": TRIAGE_ROUTER_AGENT.name,
            "display_name": TRIAGE_ROUTER_AGENT.display_name,
            "agent_type": TRIAGE_ROUTER_AGENT.agent_type,
            "duration_ms": triage_dur,
            "output": triage_output,
        },
    )

    selected_pipeline = triage_output.get("selected_pipeline", "support")
    is_renovation = (selected_pipeline == "renovation_quote")
    pipeline_ticket = build_pipeline_ticket(ticket, triage_output)
    state.ticket = pipeline_ticket

    router_step = {
        "agent": TRIAGE_ROUTER_AGENT.display_name,
        "agent_type": TRIAGE_ROUTER_AGENT.agent_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_ms": triage_dur,
        "output": triage_output,
    }
    trace_steps.append(router_step)
    if session_store and session_id:
        session_store.update_trace(session_id, router_step)


    if not is_renovation:
        return _run_support_pipeline(
            model=model,
            state=state,
            ticket=pipeline_ticket,
            actual_run_id=actual_run_id,
            run_dir=run_dir,
            session_store=session_store,
            session_id=session_id,
            trace_steps=trace_steps,
            trace_repo=trace_repo,
        )

    return _run_renovation_pipeline(
        model=model,
        state=state,
        ticket=pipeline_ticket,
        ticket_code=ticket_code,
        customer_name=customer_name,
        actual_run_id=actual_run_id,
        run_dir=run_dir,
        db_path=db_path,
        session_store=session_store,
        session_id=session_id,
        trace_steps=trace_steps,
        trace_repo=trace_repo,
        tkt_repo=tkt_repo,
        prod_repo=prod_repo,
        inv_repo=inv_repo,
        qte_repo=qte_repo,
    )


def _run_support_pipeline(
    model: ChatModel,
    state: RunState,
    ticket: dict,
    actual_run_id: str,
    run_dir: Path,
    session_store: Any,
    session_id: str | None,
    trace_steps: list,
    trace_repo: AgentTraceRepository,
) -> dict:
    for agent in AGENTS:
        result, dur = timed_agent_run(agent, model, state)
        state.add_step(agent.name, result)
        trace_repo.add_step(actual_run_id, agent.name, {"ticket": ticket}, result)

        append_jsonl(
            run_dir / "interactions.jsonl",
            {
                "run_id": actual_run_id,
                "agent": agent.name,
                "display_name": agent.display_name,
                "agent_type": agent.agent_type,
                "duration_ms": dur,
                "output": result,
            },
        )

        step_data = {
            "agent": agent.display_name,
            "agent_type": agent.agent_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "duration_ms": dur,
            "output": result,
        }
        trace_steps.append(step_data)
        if session_store and session_id:
            session_store.update_trace(session_id, step_data)

    final_output = state.final_output()
    final_output["trace"] = trace_steps
    write_json(run_dir / "final_output.json", final_output)
    write_markdown_report(run_dir / "report.md", final_output)
    return final_output


def _run_renovation_pipeline(
    model: ChatModel,
    state: RunState,
    ticket: dict,
    ticket_code: str,
    customer_name: str,
    actual_run_id: str,
    run_dir: Path,
    db_path: Path,
    session_store: Any,
    session_id: str | None,
    trace_steps: list,
    trace_repo: AgentTraceRepository,
    tkt_repo: TicketRepository,
    prod_repo: ProductRepository,
    inv_repo: InventoryRepository,
    qte_repo: QuoteRepository,
) -> dict:

    # 1. Requirement Intake Agent
    agent = RENOVATION_AGENTS["requirement_intake"]
    input_payload = {"ticket": ticket}
    result_intake, dur = timed_agent_run(agent, model, state, input_payload)
    state.add_step(agent.name, result_intake)
    trace_repo.add_step(actual_run_id, agent.name, input_payload, result_intake)
    log_step(run_dir, actual_run_id, agent, result_intake)

    # Log requirement_intake to real-time session trace
    step_data = {
        "agent": agent.display_name,
        "agent_type": agent.agent_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_ms": dur,
        "output": result_intake,
    }
    trace_steps.append(step_data)
    if session_store and session_id:
        session_store.update_trace(session_id, step_data)
    
    # Save Ticket to SQLite
    project_type = result_intake.get("project_type", "general")
    area_m2 = result_intake.get("area_m2")
    budget = result_intake.get("budget")
    customer_whatsapp = result_intake.get("customer_whatsapp") or ticket.get("customer_whatsapp")
    
    # Check if ticket already exists
    existing = tkt_repo.get_ticket(ticket_code)
    if not existing:
        tkt_repo.create_ticket(
            ticket_code=ticket_code,
            session_id=session_id,
            customer_name=customer_name,
            customer_whatsapp=customer_whatsapp,
            status="new",
            priority="medium",
            category="renovation_quote",
            summary=result_intake.get("reasoning", "Renovasi"),
            missing_info=json.dumps(result_intake.get("missing_information", [])),
        )
    else:
        tkt_repo.update_ticket(
            ticket_code,
            customer_name=customer_name,
            customer_whatsapp=customer_whatsapp or existing.get("customer_whatsapp"),
            missing_info=json.dumps(result_intake.get("missing_information", [])),
        )
    
    # 2. Product Retrieval Agent
    agent = RENOVATION_AGENTS["product_retrieval"]
    categories = result_intake.get("categories_needed") or ["keramik", "cat", "waterproofing"]
    
    # Query matching products from SQLite
    db_products = []
    for cat in categories:
        prods = prod_repo.search_products(category=cat, limit=5)
        db_products.extend(prods)
    if not db_products:
        # Fallback to general list if no matches
        db_products = prod_repo.search_products(limit=10)
    
    # Map database products to a clean list to provide as context
    catalog_context = [
        {
            "sku": p["sku"],
            "name": p["name"],
            "category": p["category"],
            "unit": p["unit"],
            "price": p["price"],
            "coverage_m2": p["coverage_m2"],
            "coverage_per_liter": p["coverage_per_liter"],
            "use_case": p["use_case"],
            "risk_note": p["risk_note"],
        }
        for p in db_products
    ]
    
    input_payload = {"catalog_products": catalog_context}
    result_retrieval, dur = timed_agent_run(agent, model, state, input_payload)
    state.add_step(agent.name, result_retrieval)
    trace_repo.add_step(actual_run_id, agent.name, input_payload, result_retrieval)
    log_step(run_dir, actual_run_id, agent, result_retrieval)

    # Log product_retrieval to real-time session trace
    step_data = {
        "agent": agent.display_name,
        "agent_type": agent.agent_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_ms": dur,
        "output": result_retrieval,
    }
    trace_steps.append(step_data)
    if session_store and session_id:
        session_store.update_trace(session_id, step_data)
    
    # 3. Inventory Snapshot Agent
    agent = RENOVATION_AGENTS["inventory_snapshot"]
    recommended_items = result_retrieval.get("recommended_products") or []

    # PRODUCT-NOT-FOUND FALLBACK: if no products found, skip to handoff with clear message
    if not recommended_items:
        fallback_note = (
            "Saya belum menemukan produk tersebut di katalog demo kami saat ini. "
            "Saya sudah mencatat permintaan Anda dan akan meneruskannya ke staff QHome Mart "
            "untuk konfirmasi harga, ketersediaan stok, dan estimasi yang lebih akurat. "
            "Tim kami akan segera menghubungi Anda."
        )
        fallback_result = {
            "selected_pipeline": "renovation_quote",
            "final": {
                "customer_reply": fallback_note,
                "staff_internal_summary": (
                    "Produk yang diminta tidak ditemukan di katalog demo. "
                    f"Tiket dari: {state.ticket.get('customer_name', 'Pelanggan')}. "
                    "Perlu konfirmasi manual dari staff toko."
                ),
                "escalate": True,
                "missing_info": ["product_catalog_gap"],
                "next_steps": ["Hubungi pelanggan untuk konfirmasi kebutuhan spesifik", "Cek katalog fisik QHome Mart"],
            },
            "agent_outputs": state.agent_outputs,
            "run_id": actual_run_id,
        }
        # Add trace for staff dashboard
        product_not_found_step = {
            "agent": "Product Retrieval — Fallback",
            "timestamp": datetime.now(UTC).isoformat(),
            "output": {"note": "Produk tidak ditemukan di katalog.", "fallback": True},
        }
        trace_steps.append(product_not_found_step)
        if session_store and session_id:
            session_store.update_trace(session_id, product_not_found_step)
        return fallback_result

    # Query inventory snapshot from SQLite
    inventory_context = []
    for item in recommended_items:

        sku = item.get("sku", "")
        snap = inv_repo.get_inventory_snapshot(sku)
        if snap:
            inventory_context.append({
                "sku": sku,
                "name": item.get("name"),
                "stock_qty": snap["stock_qty"],
                "stock_status": snap["stock_status"],
                "last_updated": snap["last_updated"],
            })
        else:
            inventory_context.append({
                "sku": sku,
                "name": item.get("name"),
                "stock_qty": 0,
                "stock_status": "unknown_need_staff_confirmation",
                "last_updated": "-",
            })
    
    input_payload = {"inventory_snapshots": inventory_context}
    result_inventory, dur = timed_agent_run(agent, model, state, input_payload)
    state.add_step(agent.name, result_inventory)
    trace_repo.add_step(actual_run_id, agent.name, input_payload, result_inventory)
    log_step(run_dir, actual_run_id, agent, result_inventory)

    # Log inventory_snapshot to real-time session trace
    step_data = {
        "agent": agent.display_name,
        "agent_type": agent.agent_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_ms": dur,
        "output": result_inventory,
    }
    trace_steps.append(step_data)
    if session_store and session_id:
        session_store.update_trace(session_id, step_data)
    
    # 4. Quantity Estimator Agent
    agent = RENOVATION_AGENTS["quantity_estimator"]
    
    # Perform deterministic calculations using tools
    area_val = area_m2 if isinstance(area_m2, (int, float)) and area_m2 > 0 else 10.0
    draft_estimations = []
    for item in recommended_items:
        sku = item.get("sku", "")
        prod = prod_repo.get_product_by_sku(sku)
        if not prod:
            if item.get("requested_qty"):
                qty = int(item.get("requested_qty") or 1)
                draft_estimations.append({
                    "sku": sku,
                    "name": item.get("name", sku),
                    "estimated_qty": qty,
                    "unit": item.get("unit", "unit"),
                    "estimation_math": f"Menggunakan jumlah eksplisit dari pesan pelanggan: {qty} {item.get('unit', 'unit')}.",
                })
            continue
        
        qty = 1
        math_reason = "Kebutuhan standard: 1 unit."
        
        if prod["category"] == "keramik" and prod["coverage_m2"]:
            qty = calculate_tile_boxes(area_val, prod["coverage_m2"])
            math_reason = f"Dihitung untuk area {area_val} m² dengan coverage {prod['coverage_m2']} m²/box + 10% waste: ceil({area_val} * 1.1 / {prod['coverage_m2']}) = {qty} box."
        elif prod["category"] == "cat" and prod["coverage_per_liter"]:
            liters = calculate_paint_liters(area_val, prod["coverage_per_liter"])
            qty = int(math.ceil(liters / 5.0)) if "5L" in prod["name"] else int(math.ceil(liters))
            math_reason = f"Dihitung untuk area {area_val} m² (2 lapis) dengan coverage {prod['coverage_per_liter']} m²/liter + 10% waste: {liters} liter. Dibulatkan ke {qty} {prod['unit']}."
        elif prod["category"] in {"perekat keramik", "nat keramik"} and prod["coverage_m2"]:
            qty = int(math.ceil(area_val / prod["coverage_m2"]))
            math_reason = f"Companion material untuk area {area_val} m² dengan coverage {prod['coverage_m2']} m²/{prod['unit']}: ceil({area_val} / {prod['coverage_m2']}) = {qty} {prod['unit']}."
    
        draft_estimations.append({
            "sku": sku,
            "name": prod["name"],
            "estimated_qty": qty,
            "unit": prod["unit"],
            "estimation_math": math_reason,
        })
    
    input_payload = {"draft_material_estimations": draft_estimations, "area_m2": area_val}
    result_estimator, dur = timed_agent_run(agent, model, state, input_payload)
    state.add_step(agent.name, result_estimator)
    trace_repo.add_step(actual_run_id, agent.name, input_payload, result_estimator)
    log_step(run_dir, actual_run_id, agent, result_estimator)

    # Log quantity_estimator to real-time session trace
    step_data = {
        "agent": agent.display_name,
        "agent_type": agent.agent_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_ms": dur,
        "output": result_estimator,
    }
    trace_steps.append(step_data)
    if session_store and session_id:
        session_store.update_trace(session_id, step_data)
    
    # 5. Quote Builder Agent
    agent = RENOVATION_AGENTS["quote_builder"]
    final_estimations = result_estimator.get("estimations") or draft_estimations
    
    # Calculate subtotals and estimated total
    quote_items = []
    recommended_by_sku = {item.get("sku"): item for item in recommended_items}
    for est in final_estimations:
        sku = est.get("sku", "")
        qty = est.get("estimated_qty", 1)
        prod = prod_repo.get_product_by_sku(sku)
        if prod:
            price = prod["price"]
            subtotal = qty * price
            quote_items.append({
                "sku": sku,
                "name": prod["name"],
                "qty": qty,
                "unit": est.get("unit") or prod["unit"],
                "unit_price": price,
                "subtotal": subtotal,
            })
        else:
            item = recommended_by_sku.get(sku, {})
            price = int(item.get("unit_price") or item.get("price") or 0)
            subtotal = qty * price
            quote_items.append({
                "sku": sku,
                "name": est.get("name") or item.get("name") or sku,
                "qty": qty,
                "unit": est.get("unit") or item.get("unit") or "unit",
                "unit_price": price,
                "subtotal": subtotal,
            })
    
    estimated_total = calculate_total(quote_items)
    budget_val = budget if isinstance(budget, (int, float)) and budget > 0 else None
    budget_status = determine_budget_status(estimated_total, budget_val)
    
    input_payload = {
        "calculated_draft": {
            "items": quote_items,
            "estimated_total": estimated_total,
            "budget": budget_val,
            "budget_status": budget_status,
        }
    }
    result_quote, dur = timed_agent_run(agent, model, state, input_payload)
    state.add_step(agent.name, result_quote)
    trace_repo.add_step(actual_run_id, agent.name, input_payload, result_quote)
    log_step(run_dir, actual_run_id, agent, result_quote)

    # Log quote_builder to real-time session trace
    step_data = {
        "agent": agent.display_name,
        "agent_type": agent.agent_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_ms": dur,
        "output": result_quote,
    }
    trace_steps.append(step_data)
    if session_store and session_id:
        session_store.update_trace(session_id, step_data)
    
    # 6. Risk & Policy Verifier Agent (Critic / DEBATE LOOP)
    agent = RENOVATION_AGENTS["risk_policy_verifier"]
    
    # Query policies from DB
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM policies")
    db_policies = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    input_payload = {
        "draft_quote": result_quote,
        "inventory_status_ok": result_inventory.get("stock_status_ok", True),
        "inventory_alerts": result_inventory.get("inventory_alerts", []),
        "missing_information": result_intake.get("missing_information", []),
        "policies": db_policies,
    }
    result_verifier, dur = timed_agent_run(agent, model, state, input_payload)
    state.add_step(agent.name, result_verifier)
    trace_repo.add_step(actual_run_id, agent.name, input_payload, result_verifier)
    log_step(run_dir, actual_run_id, agent, result_verifier)

    # Log risk_policy_verifier to real-time session trace
    step_data = {
        "agent": agent.display_name,
        "agent_type": agent.agent_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_ms": dur,
        "output": result_verifier,
    }
    trace_steps.append(step_data)
    if session_store and session_id:
        session_store.update_trace(session_id, step_data)
    
    # ACTIVE DEBATE & REVISION LOOP:
    # If verifier flags policy violations, we force Quote Builder to reflect and revise!
    if result_verifier.get("revision_required", False):
        agent_quote = RENOVATION_AGENTS["quote_builder"]
        revision_input = {
            "calculated_draft": {
                "items": quote_items,
                "estimated_total": estimated_total,
                "budget": budget_val,
                "budget_status": budget_status,
            },
            "criticism_feedback": result_verifier.get("criticism_debate_log", ""),
            "instructions": "REVISE your quotation notes and warnings to address the Critic's policy violations strictly. Do not make claims of real-time stock or final prices. Ask for WhatsApp actively."
        }
        # Run Quote Builder second pass
        revised_result, rev_dur = timed_agent_run(agent_quote, model, state, revision_input)
        state.steps[-2].output = revised_result  # Replace previous quote output in state trace
        result_quote = revised_result
        # Log revision step to DB trace
        trace_repo.add_step(actual_run_id, "quote_builder_revision", revision_input, revised_result)
        result_verifier["revision_applied"] = True

        # Append to live trace for staff dashboard visibility
        revision_step = {
            "agent": "Quote Builder (Revisi)",
            "agent_type": "Quotation Builder Agent",
            "timestamp": datetime.now(UTC).isoformat(),
            "duration_ms": rev_dur,
            "output": revised_result,
        }
        trace_steps.append(revision_step)
        if session_store and session_id:
            session_store.update_trace(session_id, revision_step)
    
    # Save finalized quote to SQLite
    quote_code = result_quote.get("quote_code") or f"QTE-{actual_run_id[4:9].upper()}"
    qte_repo.create_quote(
        quote_code=quote_code,
        ticket_code=ticket_code,
        estimated_total=result_quote.get("estimated_total", estimated_total),
        budget=budget_val,
        budget_status=result_quote.get("budget_status", budget_status),
        risk_level=result_verifier.get("risk_level", "medium"),
        notes=result_quote.get("notes", ""),
    )
    for qitem in (result_quote.get("line_items") or quote_items):
        qte_repo.add_quote_item(
            quote_code=quote_code,
            sku=qitem["sku"],
            name=qitem["name"],
            qty=qitem["qty"],
            unit=qitem["unit"],
            unit_price=qitem["unit_price"],
            subtotal=qitem["subtotal"],
        )
    
    # 7. Staff Handoff & Customer Response Agent
    agent = RENOVATION_AGENTS["staff_handoff_response"]
    input_payload = {
        "final_quote": result_quote,
        "verifier_audit": result_verifier,
    }
    result_handoff, dur = timed_agent_run(agent, model, state, input_payload)
    state.add_step(agent.name, result_handoff)
    trace_repo.add_step(actual_run_id, agent.name, input_payload, result_handoff)
    log_step(run_dir, actual_run_id, agent, result_handoff)

    # Log staff_handoff_response to real-time session trace
    step_data = {
        "agent": agent.display_name,
        "agent_type": agent.agent_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_ms": dur,
        "output": result_handoff,
    }
    trace_steps.append(step_data)
    if session_store and session_id:
        session_store.update_trace(session_id, step_data)
    
    # Save to JSON outputs
    final_output = build_final_output(
        run_id=actual_run_id,
        ticket=ticket,
        ticket_code=ticket_code,
        intake=result_intake,
        retrieval=result_retrieval,
        inventory=result_inventory,
        estimator=result_estimator,
        quote=result_quote,
        verifier=result_verifier,
        handoff=result_handoff,
        steps=trace_steps,
    )
    
    write_json(run_dir / "final_output.json", final_output)
    write_markdown_report(run_dir / "report.md", final_output)
    return final_output


def timed_agent_run(agent: Any, model: Any, state: Any, additional_payload: dict | None = None) -> tuple[dict, int]:
    """Run an agent and return (result, duration_ms). Pure wrapper — does not alter output."""
    t0 = time.monotonic()
    result = agent.run(model, state, additional_payload=additional_payload)
    duration_ms = int((time.monotonic() - t0) * 1000)
    return result, duration_ms


def log_step(run_dir: Path, run_id: str, agent: Any, output: dict) -> None:
    append_jsonl(
        run_dir / "interactions.jsonl",
        {
            "run_id": run_id,
            "agent": agent.name,
            "display_name": agent.display_name,
            "agent_type": getattr(agent, "agent_type", "LLM Reasoning Agent"),
            "output": output,
        },
    )


def build_final_output(
    run_id: str,
    ticket: dict,
    ticket_code: str,
    intake: dict,
    retrieval: dict,
    inventory: dict,
    estimator: dict,
    quote: dict,
    verifier: dict,
    handoff: dict,
    steps: list[AgentStep],
) -> dict[str, Any]:
    # Normalize values for dashboard UI
    prio_map = {"low": "low", "medium": "medium", "high": "high"}
    risk_prio = prio_map.get(verifier.get("risk_level", "medium").lower(), "medium")

    final_dict = {
        "intent": intake.get("project_type", "product_advice"),
        "category": "renovation_quote",
        "priority": risk_prio,
        "escalate": verifier.get("risk_level") == "high" or handoff.get("contact_required", False),
        "escalation_team": "sales_logistics" if verifier.get("risk_level") == "high" else "customer_service",
        "customer_reply": handoff.get("customer_reply", ""),
        "internal_next_steps": handoff.get("internal_next_steps", []),
        
        # New quotation & verifier data
        "ticket_code": ticket_code,
        "quote_code": quote.get("quote_code"),
        "estimated_total": quote.get("estimated_total", 0),
        "budget": quote.get("budget"),
        "budget_status": quote.get("budget_status", "unknown_budget"),
        "line_items": quote.get("line_items", []),
        "notes": quote.get("notes", ""),
        
        # Risk & verifier
        "risk_level": verifier.get("risk_level", "medium"),
        "issues_found": verifier.get("issues_found", []),
        "criticism_debate_log": verifier.get("criticism_debate_log", ""),
        "inventory_alerts": inventory.get("inventory_alerts", []),
        
        # Intake
        "missing_information": intake.get("missing_information", []),
        "staff_summary": handoff.get("staff_summary", ""),
        "contact_required": handoff.get("contact_required", False),
        "requested_contact_fields": handoff.get("requested_contact_fields", []),
    }

    triage_output = {}
    if steps and len(steps) > 0:
        first_step = steps[0]
        if isinstance(first_step, dict):
            triage_output = first_step.get("output", {})
        else:
            triage_output = getattr(first_step, "output", {})

    return {
        "run_id": run_id,
        "ticket": ticket,
        "final": final_dict,
        "agent_outputs": {
            "triage_router": triage_output,
            "requirement_intake": intake,
            "product_retrieval": retrieval,
            "inventory_snapshot": inventory,
            "quantity_estimator": estimator,
            "quote_builder": quote,
            "risk_policy_verifier": verifier,
            "staff_handoff_response": handoff,
        },
        "trace": [
            {
                "agent": step.get("agent") if isinstance(step, dict) else getattr(step, "agent", ""),
                "agent_type": step.get("agent_type") if isinstance(step, dict) else getattr(step, "agent_type", None),
                "timestamp": step.get("timestamp") if isinstance(step, dict) else getattr(step, "timestamp", ""),
                "duration_ms": step.get("duration_ms") if isinstance(step, dict) else getattr(step, "duration_ms", None),
                "output": step.get("output") if isinstance(step, dict) else getattr(step, "output", {}),
            }
            for step in steps
        ],
    }
