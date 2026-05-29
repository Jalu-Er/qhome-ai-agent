from __future__ import annotations

import math
from typing import Any


def calculate_tile_boxes(area_m2: float, coverage_m2: float, waste_percent: float = 10.0) -> int:
    """Calculate ceramic/tile box requirement.
    
    Args:
        area_m2: Total floor/wall area in square meters.
        coverage_m2: Square meters covered by one box.
        waste_percent: Multiplier for wastage/cutting allowance.
        
    Returns:
        Ceiled box count (int).
    """
    if area_m2 <= 0 or coverage_m2 <= 0:
        return 0
    total_area = area_m2 * (1.0 + (waste_percent / 100.0))
    return int(math.ceil(total_area / coverage_m2))


def calculate_paint_liters(
    area_m2: float, coverage_per_liter: float, coats: int = 2, waste_percent: float = 10.0
) -> float:
    """Calculate paint requirement in liters.
    
    Args:
        area_m2: Total wall area in square meters.
        coverage_per_liter: Coverage rate per liter.
        coats: Number of paint layers/coats to apply.
        waste_percent: Multiplier for wastage/cutting allowance.
        
    Returns:
        Calculated paint volume in liters.
    """
    if area_m2 <= 0 or coverage_per_liter <= 0 or coats <= 0:
        return 0.0
    total_area_to_paint = area_m2 * coats
    base_liters = total_area_to_paint / coverage_per_liter
    return round(base_liters * (1.0 + (waste_percent / 100.0)), 2)


def calculate_total(items: list[dict[str, Any]]) -> int:
    """Calculate the estimated total price for quote items.
    
    Args:
        items: List of dictionary records, each containing 'qty' and 'unit_price' or 'subtotal'.
        
    Returns:
        Summed total cost (int).
    """
    total = 0
    for item in items:
        subtotal = item.get("subtotal")
        if subtotal is not None:
            total += int(subtotal)
        else:
            qty = int(item.get("qty", 0))
            price = int(item.get("unit_price", 0))
            total += qty * price
    return total


def determine_budget_status(total: int, budget: int | None) -> str:
    """Classify the budget safety of the draft quotation.
    
    Args:
        total: Estimated total price of products/services.
        budget: Customer's stated maximum budget capacity.
        
    Returns:
        Classification status string.
    """
    if budget is None or budget <= 0:
        return "unknown_budget"
    
    if total <= budget:
        if total >= budget * 0.9:
            return "near_budget_limit"
        return "within_budget"
    
    return "over_budget"


def verify_quote_risks(
    quote: dict[str, Any], missing_info: list[str], inventory_notes: list[str]
) -> list[str]:
    """Inspect draft quotation details and contexts to flag any compliance risks.
    
    Args:
        quote: Dictionary representation of the draft quote.
        missing_info: List of missing requirement fields identified.
        inventory_notes: List of inventory/stock snapshot alerts.
        
    Returns:
        List of compliance risk tags or warnings.
    """
    risks = []
    
    # 1. Price is not final warning (mandatory)
    risks.append("Harga akhir, diskon, dan ongkos kirim belum final dan harus divalidasi oleh staff.")
    
    # 2. Stock is snapshot warning (mandatory)
    risks.append("Stok adalah snapshot data demo, bukan stok real-time.")
    
    # 3. WhatsApp contact is missing
    whatsapp = quote.get("customer_whatsapp") or quote.get("whatsapp")
    if not whatsapp:
        risks.append("Nomor WhatsApp/HP pelanggan belum terverifikasi untuk follow-up staff.")
        
    # 4. Incomplete measurements / dimensions
    if any("ukuran" in info.lower() or "area" in info.lower() or "panjang" in info.lower() or "lebar" in info.lower() for info in missing_info):
        risks.append("Ukuran ruangan belum lengkap, estimasi material bersifat tentatif.")
        
    # 5. Over budget
    budget_status = quote.get("budget_status")
    if budget_status == "over_budget":
        risks.append("Total estimasi quotation melebihi kapasitas anggaran (budget) pelanggan.")
        
    # 6. Low stock flag
    if any("low_stock" in note or "habis" in note or "0" in note for note in inventory_notes):
        risks.append("Beberapa produk yang direkomendasikan memiliki ketersediaan stok terbatas/habis.")
        
    # 7. Renovation field verification note
    risks.append("Pekerjaan renovasi membutuhkan survey lapangan oleh staff/mitra tukang.")
    
    return risks
