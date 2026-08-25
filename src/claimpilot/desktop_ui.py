from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from .demo_surface import DemoDashboard


class DemoDesktopController:
    """Thin controller that exposes the demo backend as a desktop-friendly API."""

    def __init__(self, dashboard: DemoDashboard | None = None) -> None:
        self.dashboard = dashboard or DemoDashboard()
        self.last_action = "idle"

    def trigger_scenario(self, scenario: str) -> dict[str, Any]:
        result = self.dashboard.trigger_scenario(scenario)
        self.last_action = result["action"]
        return result

    def snapshot(self) -> dict[str, Any]:
        orders = self.dashboard.order_store.all()
        audit_records = self.dashboard.audit_store.all()

        pending_decisions = sum(
            1
            for record in audit_records
            if record.action == "needs_decision" and record.status in {"pending_user", "pending"}
        )

        latest = audit_records[-1] if audit_records else None
        latest_audit = (
            f"{latest.action}:{latest.status}:{latest.details}"
            if latest is not None
            else "No activity yet"
        )

        return {
            "active_orders": len(orders),
            "pending_decisions": pending_decisions,
            "last_action": self.last_action,
            "latest_audit": latest_audit,
            "orders": [
                {
                    "order_id": order.order_id,
                    "item_name": order.item_name,
                    "merchant": order.merchant or "Demo Merchant",
                    "current_price": f"${order.current_price:.2f}",
                    "purchase_price": f"${order.purchase_price:.2f}",
                }
                for order in orders
            ],
            "audit_records": [
                {
                    "action": record.action,
                    "status": record.status,
                    "details": record.details,
                    "order_id": record.order_id,
                }
                for record in audit_records
            ],
        }


class DemoDesktopApp(tk.Tk):
    """Minimal desktop UI for demoing the ClaimPilot flow in a local environment."""

    def __init__(self) -> None:
        super().__init__()
        self.title("ClaimPilot Demo Console")
        self.geometry("1100x720")
        self.minsize(980, 620)
        self.configure(bg="#f3f4f6")

        self.controller = DemoDesktopController()
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)

        left_panel = ttk.Frame(self, padding=16)
        left_panel.grid(row=0, column=0, sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)

        right_panel = ttk.Frame(self, padding=16)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)

        title = ttk.Label(left_panel, text="ClaimPilot Demo", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        ttk.Label(left_panel, text="Scenario triggers", font=("Segoe UI", 12, "bold")).grid(
            row=1, column=0, sticky="w", pady=(0, 8)
        )

        scenarios = [
            ("Price Drop", "price_drop"),
            ("Damaged Item", "damaged_item"),
            ("Return Window", "return_window"),
        ]

        self.scenario_buttons: list[ttk.Button] = []
        for index, (label, scenario) in enumerate(scenarios, start=2):
            button = ttk.Button(
                left_panel,
                text=label,
                command=lambda key=scenario: self._run_scenario(key),
                width=22,
            )
            button.grid(row=index, column=0, sticky="ew", pady=4)
            self.scenario_buttons.append(button)

        summary = ttk.LabelFrame(left_panel, text="Live summary", padding=(10, 8))
        summary.grid(row=6, column=0, sticky="ew", pady=(18, 8))
        summary.grid_columnconfigure(1, weight=1)

        self.active_var = tk.StringVar(value="0")
        self.pending_var = tk.StringVar(value="0")
        self.last_action_var = tk.StringVar(value="idle")

        ttk.Label(summary, text="Active orders").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(summary, textvariable=self.active_var, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=1, sticky="e", padx=6, pady=4
        )

        ttk.Label(summary, text="Pending decisions").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(summary, textvariable=self.pending_var, font=("Segoe UI", 11, "bold")).grid(
            row=1, column=1, sticky="e", padx=6, pady=4
        )

        ttk.Label(summary, text="Last action").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(summary, textvariable=self.last_action_var, font=("Segoe UI", 11, "bold")).grid(
            row=2, column=1, sticky="e", padx=6, pady=4
        )

        self.status_var = tk.StringVar(value="Ready")
        status = ttk.LabelFrame(left_panel, text="Status", padding=(10, 8))
        status.grid(row=7, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(status, textvariable=self.status_var, wraplength=260, justify="left").grid(
            row=0, column=0, sticky="w"
        )

        orders_frame = ttk.LabelFrame(right_panel, text="Orders", padding=(8, 8))
        orders_frame.grid(row=0, column=0, sticky="nsew")
        orders_frame.grid_columnconfigure(0, weight=1)
        orders_frame.grid_rowconfigure(0, weight=1)

        columns = ("order_id", "item", "merchant", "price")
        self.orders_tree = ttk.Treeview(orders_frame, columns=columns, show="headings", height=7)
        self.orders_tree.heading("order_id", text="Order ID")
        self.orders_tree.heading("item", text="Item")
        self.orders_tree.heading("merchant", text="Merchant")
        self.orders_tree.heading("price", text="Price")
        self.orders_tree.column("order_id", width=150, anchor="center")
        self.orders_tree.column("item", width=200, anchor="w")
        self.orders_tree.column("merchant", width=160, anchor="w")
        self.orders_tree.column("price", width=100, anchor="e")
        self.orders_tree.grid(row=0, column=0, sticky="nsew")

        audit_frame = ttk.LabelFrame(right_panel, text="Audit timeline", padding=(8, 8))
        audit_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        audit_frame.grid_columnconfigure(0, weight=1)
        audit_frame.grid_rowconfigure(0, weight=1)

        self.audit_text = tk.Text(audit_frame, wrap="word", height=14, font=("SF Mono", 10), state="disabled")
        self.audit_text.grid(row=0, column=0, sticky="nsew")

    def _run_scenario(self, scenario: str) -> None:
        result = self.controller.trigger_scenario(scenario)
        self.status_var.set(
            f"{result['action']} | {result['order_id']} | {result['reason']}"
        )
        self._refresh()

    def _refresh(self) -> None:
        snapshot = self.controller.snapshot()
        self.active_var.set(str(snapshot["active_orders"]))
        self.pending_var.set(str(snapshot["pending_decisions"]))
        self.last_action_var.set(snapshot["last_action"])

        for row in self.orders_tree.get_children():
            self.orders_tree.delete(row)

        for order in snapshot["orders"]:
            self.orders_tree.insert(
                "",
                "end",
                values=(
                    order["order_id"],
                    order["item_name"],
                    order["merchant"],
                    order["current_price"],
                ),
            )

        self.audit_text.configure(state="normal")
        self.audit_text.delete("1.0", "end")
        if snapshot["audit_records"]:
            for record in reversed(snapshot["audit_records"][-8:]):
                line = (
                    f"{record['action']} | {record['status']} | {record['order_id']} | {record['details']}\n"
                )
                self.audit_text.insert("end", line)
        else:
            self.audit_text.insert("end", "No activity yet\n")
        self.audit_text.configure(state="disabled")


def main() -> None:
    app = DemoDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
