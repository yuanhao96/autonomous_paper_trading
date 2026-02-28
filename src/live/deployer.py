"""Deployer — deploy validated strategies to paper/live trading via IBKR.

Flow:
1. Pre-deployment checks (audit gate, risk engine)
2. Connect to broker (IBKR or PaperBroker)
3. Compute target positions from strategy signals
4. Execute rebalancing orders
5. Record deployment state and trades
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.core.config import Preferences, Settings, load_preferences
from src.core.db import get_engine, init_db
from src.live.broker import BrokerAPI, IBKRBroker, PaperBroker
from src.live.models import Deployment, LiveSnapshot, Position, TradeRecord
from src.live.nt_signals import compute_nt_signals
from src.live.signals import compute_target_weights
from src.risk.auditor import Auditor, AuditReport
from src.risk.engine import RiskEngine, RiskViolation
from src.strategies.spec import StrategyResult, StrategySpec
from src.universe.static import get_universe_asset_class

logger = logging.getLogger(__name__)


class DeploymentCheck:
    """Single pre-deployment check result."""

    def __init__(self, name: str, passed: bool, message: str) -> None:
        self.name = name
        self.passed = passed
        self.message = message


class Deployer:
    """Manages strategy deployment lifecycle.

    Usage:
        deployer = Deployer()
        checks = deployer.validate_readiness(spec, validation_result)
        if all(c.passed for c in checks):
            deployment = deployer.deploy(spec, symbols, prices)
            deployer.rebalance(deployment, prices)
    """

    def __init__(
        self,
        broker: BrokerAPI | None = None,
        settings: Settings | None = None,
        preferences: Preferences | None = None,
        engine: Engine | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._prefs = preferences or load_preferences()
        self._risk_engine = RiskEngine(preferences=self._prefs)
        self._auditor = Auditor(preferences=self._prefs)
        self._engine = engine or get_engine()
        init_db(self._engine)
        # Per-deployment broker cache: each deployment gets isolated state
        self._brokers: dict[str, BrokerAPI] = {}
        # Injected broker (for tests) — assigned to first deployment
        self._injected_broker = broker

    def _get_broker(
        self, mode: str = "paper", deployment_id: str = "",
    ) -> BrokerAPI:
        """Get or create a broker connection for a specific deployment.

        Each deployment gets its own broker instance so positions, cash,
        and state don't bleed across deployments in the same mode.

        Modes:
            paper — local PaperBroker simulation (no external deps)
            ibkr_paper — IBKR paper trading account (port 7497)
            live — IBKR live trading (port 7496)
        """
        key = deployment_id or mode
        if key in self._brokers:
            return self._brokers[key]

        # Use injected broker (test support) for the first deployment
        if self._injected_broker is not None:
            self._brokers[key] = self._injected_broker
            self._injected_broker = None
            return self._brokers[key]

        if mode == "paper":
            initial_cash = self._settings.get("live.initial_cash", 100_000)
            broker = PaperBroker(initial_cash=initial_cash)
        elif mode == "ibkr_paper":
            host = self._settings.get("live.ibkr_host", "127.0.0.1")
            port = self._settings.get("live.ibkr_paper_port", 7497)
            client_id = self._settings.get("live.ibkr_client_id", 1)
            broker = IBKRBroker(host=host, port=port, client_id=client_id)
        else:  # "live"
            host = self._settings.get("live.ibkr_host", "127.0.0.1")
            port = self._settings.get("live.ibkr_live_port", 7496)
            client_id = self._settings.get("live.ibkr_client_id", 1)
            broker = IBKRBroker(host=host, port=port, client_id=client_id)

        self._brokers[key] = broker
        return broker

    def validate_readiness(
        self,
        spec: StrategySpec,
        screen_result: StrategyResult,
        validation_result: StrategyResult | None = None,
    ) -> list[DeploymentCheck]:
        """Pre-deployment validation checklist."""
        checks: list[DeploymentCheck] = []

        # 1. Risk engine check
        violations = self._risk_engine.check_spec(spec)
        checks.append(DeploymentCheck(
            name="risk_limits",
            passed=len(violations) == 0,
            message="OK" if not violations else f"{len(violations)} violations: {violations[0].message}",
        ))

        # 2. Audit gate
        if self._prefs.audit_gate_enabled:
            audit = self._auditor.audit(screen_result, validation_result)
            checks.append(DeploymentCheck(
                name="audit_gate",
                passed=audit.passed,
                message="All checks passed" if audit.passed else f"Failed: {[c.name for c in audit.failed_checks]}",
            ))
        else:
            checks.append(DeploymentCheck(
                name="audit_gate",
                passed=True,
                message="Audit gate disabled",
            ))

        # 3. Screening passed
        checks.append(DeploymentCheck(
            name="screening_passed",
            passed=screen_result.passed,
            message="OK" if screen_result.passed else f"Failed: {screen_result.failure_reason}",
        ))

        # 4. Validation passed (required)
        if validation_result is not None:
            checks.append(DeploymentCheck(
                name="validation_passed",
                passed=validation_result.passed,
                message="OK" if validation_result.passed else f"Failed: {validation_result.failure_reason}",
            ))
        else:
            checks.append(DeploymentCheck(
                name="validation_passed",
                passed=False,
                message="No validation result — validation is required before deployment",
            ))

        # 5. Drawdown check
        dd_violations = self._risk_engine.check_result_drawdown(screen_result.max_drawdown)
        checks.append(DeploymentCheck(
            name="drawdown_limit",
            passed=len(dd_violations) == 0,
            message="OK" if not dd_violations else dd_violations[0].message,
        ))

        # 6. Asset class check (from spec's universe)
        if spec.universe_spec is not None:
            asset_class = spec.universe_spec.asset_class
        else:
            asset_class = get_universe_asset_class(spec.universe_id)
        ac_violations = self._risk_engine.check_asset_class(asset_class)
        checks.append(DeploymentCheck(
            name="asset_class_allowed",
            passed=len(ac_violations) == 0,
            message="OK" if not ac_violations else ac_violations[0].message,
        ))

        return checks

    def deploy(
        self,
        spec: StrategySpec,
        symbols: list[str],
        mode: str = "paper",
        account_id: str = "",
    ) -> Deployment:
        """Create a new deployment and connect to broker.

        Args:
            spec: Validated strategy specification.
            symbols: Symbols to trade.
            mode: "paper" or "live".
            account_id: Broker account ID (auto-detected if empty).

        Returns:
            Deployment record.
        """
        initial_cash = self._settings.get("live.initial_cash", 100_000)

        deployment = Deployment(
            spec_id=spec.id,
            account_id=account_id or f"{mode}_default",
            mode=mode,
            symbols=symbols,
            initial_cash=initial_cash,
        )

        # Connect broker — keyed by deployment ID for isolation
        broker = self._get_broker(mode, deployment.id)
        if not broker.is_connected():
            broker.connect()

        # Activate deployment
        deployment.status = "active"
        self._save_deployment(deployment)

        logger.info(
            "Deployed strategy %s to %s trading: %d symbols, $%.0f initial cash",
            spec.id, mode, len(symbols), initial_cash,
        )
        return deployment

    def rebalance(
        self,
        deployment: Deployment,
        spec: StrategySpec,
        prices: dict[str, Any],
    ) -> list[TradeRecord]:
        """Rebalance positions to match strategy signals.

        Args:
            deployment: Active deployment.
            spec: Strategy specification.
            prices: {symbol: DataFrame} with OHLCV data.

        Returns:
            List of executed trades.
        """
        if not deployment.is_active:
            logger.warning("Cannot rebalance inactive deployment %s", deployment.id)
            return []

        broker = self._get_broker(deployment.mode, deployment.id)
        if not broker.is_connected():
            broker.connect()

        # Auto-set prices for PaperBroker from the provided price data
        if isinstance(broker, PaperBroker):
            current_prices = {
                s: self._get_latest_price(prices, s)
                for s in deployment.symbols
                if self._get_latest_price(prices, s) > 0
            }
            if current_prices:
                broker.set_prices(current_prices)

        # Compute target signals via NT micro-backtest (falls back to signal-based)
        signals = compute_nt_signals(spec, prices)
        target_weights = compute_target_weights(spec, signals)

        # Get current state
        account = broker.get_account_summary()
        equity = account.get("equity", deployment.initial_cash)
        current_positions = broker.get_positions()
        current_holdings = {p.symbol: p.quantity for p in current_positions}

        # Enforce cash reserve: reduce target weights so min_cash_reserve_pct is kept
        min_cash_pct = self._prefs.risk_limits.min_cash_reserve_pct
        max_invest_pct = 1.0 - min_cash_pct
        total_weight = sum(target_weights.values())
        if total_weight > max_invest_pct:
            scale = max_invest_pct / total_weight if total_weight > 0 else 1.0
            target_weights = {s: w * scale for s, w in target_weights.items()}
            logger.info(
                "Scaled weights by %.2f to maintain %.1f%% cash reserve",
                scale, min_cash_pct * 100,
            )

        # Enforce leverage limit: total exposure must not exceed max_leverage * equity
        max_leverage = self._prefs.risk_limits.max_leverage
        total_target_exposure = sum(
            abs(target_weights.get(s, 0.0)) * equity for s in deployment.symbols
        )
        leverage_violations = self._risk_engine.check_leverage(
            total_target_exposure, equity,
        )
        if leverage_violations:
            if total_target_exposure > 0:
                scale = (max_leverage * equity) / total_target_exposure
            else:
                scale = 1.0
            target_weights = {s: w * scale for s, w in target_weights.items()}
            logger.warning(
                "Scaled weights by %.2f to enforce leverage limit %.2fx",
                scale, max_leverage,
            )

        # Calculate target shares
        trades: list[TradeRecord] = []
        for symbol in deployment.symbols:
            target_weight = target_weights.get(symbol, 0.0)
            current_price = self._get_latest_price(prices, symbol)
            if current_price <= 0:
                continue

            target_value = equity * target_weight
            target_shares = int(target_value / current_price)
            current_shares = current_holdings.get(symbol, 0)
            delta = target_shares - current_shares

            if delta > 0:
                trade = broker.place_order(symbol, "buy", delta)
                if trade:
                    trades.append(trade)
                    deployment.trades.append(trade)
            elif delta < 0:
                trade = broker.place_order(symbol, "sell", abs(delta))
                if trade:
                    trades.append(trade)
                    deployment.trades.append(trade)

        # Take snapshot
        snapshot = self._take_snapshot(deployment, broker)
        deployment.snapshots.append(snapshot)

        # Persist
        self._save_trades(deployment.id, trades)
        self._save_snapshot(snapshot)

        logger.info(
            "Rebalanced deployment %s: %d trades, equity=$%.0f",
            deployment.id, len(trades), snapshot.equity,
        )
        return trades

    def stop(self, deployment: Deployment) -> None:
        """Stop a deployment and close all positions."""
        if not deployment.is_active:
            return

        broker = self._get_broker(deployment.mode, deployment.id)
        if broker.is_connected():
            # Cancel open orders
            broker.cancel_all_orders()
            # Close all positions
            for pos in broker.get_positions():
                if pos.quantity > 0:
                    broker.place_order(pos.symbol, "sell", pos.quantity)

        deployment.status = "stopped"
        deployment.stopped_at = datetime.utcnow()
        self._save_deployment(deployment)
        logger.info("Stopped deployment %s", deployment.id)

    def take_snapshot(self, deployment: Deployment) -> LiveSnapshot | None:
        """Take a fresh snapshot from the broker and persist it.

        Used by monitoring to get current state before comparison.
        Returns None if broker is not connected.
        """
        if not deployment.is_active:
            return None

        broker = self._get_broker(deployment.mode, deployment.id)
        if not broker.is_connected():
            return None

        snapshot = self._take_snapshot(deployment, broker)
        deployment.snapshots.append(snapshot)
        self._save_snapshot(snapshot)
        return snapshot

    def get_deployment(self, deployment_id: str) -> Deployment | None:
        """Load a deployment from the database."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM deployments WHERE id = :id"),
                {"id": deployment_id},
            ).fetchone()
        if row is None:
            return None
        d = Deployment(
            id=row[0],
            spec_id=row[1],
            account_id=row[2],
            mode=row[3],
            status=row[4],
            symbols=json.loads(row[5]),
            initial_cash=row[6],
            config=json.loads(row[7]),
            started_at=datetime.fromisoformat(row[8]),
            stopped_at=datetime.fromisoformat(row[9]) if row[9] else None,
        )
        d.snapshots = self._load_snapshots(d.id)
        d.trades = self._load_trades(d.id)
        return d

    def list_deployments(self, status: str | None = None) -> list[Deployment]:
        """List all deployments, optionally filtered by status."""
        query = "SELECT * FROM deployments"
        params: dict[str, Any] = {}
        if status:
            query += " WHERE status = :status"
            params["status"] = status
        query += " ORDER BY started_at DESC"

        with self._engine.connect() as conn:
            rows = conn.execute(text(query), params).fetchall()

        deployments = []
        for r in rows:
            d = Deployment(
                id=r[0], spec_id=r[1], account_id=r[2], mode=r[3],
                status=r[4], symbols=json.loads(r[5]),
                initial_cash=r[6],
                config=json.loads(r[7]),
                started_at=datetime.fromisoformat(r[8]),
                stopped_at=(
                    datetime.fromisoformat(r[9]) if r[9] else None
                ),
            )
            d.snapshots = self._load_snapshots(d.id)
            d.trades = self._load_trades(d.id)
            deployments.append(d)
        return deployments

    # ── Private helpers ──────────────────────────────────────────────

    def _load_snapshots(
        self, deployment_id: str,
    ) -> list[LiveSnapshot]:
        """Load snapshots from DB for a deployment."""
        with self._engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT deployment_id, equity, cash, daily_pnl,"
                " total_pnl, total_trades, total_fees,"
                " positions_json, recorded_at"
                " FROM snapshots"
                " WHERE deployment_id = :did"
                " ORDER BY recorded_at ASC"
            ), {"did": deployment_id}).fetchall()
        snapshots: list[LiveSnapshot] = []
        for r in rows:
            positions_data = json.loads(r[7]) if r[7] else []
            positions = [
                Position(
                    symbol=p["symbol"],
                    quantity=p["quantity"],
                    avg_cost=p["avg_cost"],
                    market_value=p["market_value"],
                    unrealized_pnl=0.0,
                )
                for p in positions_data
            ]
            snapshots.append(LiveSnapshot(
                deployment_id=r[0],
                timestamp=datetime.fromisoformat(r[8]),
                equity=r[1],
                cash=r[2],
                positions=positions,
                daily_pnl=r[3],
                total_pnl=r[4],
                total_trades=r[5],
                total_fees=r[6],
            ))
        return snapshots

    def _load_trades(
        self, deployment_id: str,
    ) -> list[TradeRecord]:
        """Load trades from DB for a deployment."""
        with self._engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT symbol, side, quantity, price,"
                " commission, order_id, executed_at"
                " FROM trades"
                " WHERE deployment_id = :did"
                " ORDER BY executed_at ASC"
            ), {"did": deployment_id}).fetchall()
        return [
            TradeRecord(
                symbol=r[0],
                side=r[1],
                quantity=r[2],
                price=r[3],
                commission=r[4],
                order_id=r[5],
                timestamp=datetime.fromisoformat(r[6]),
            )
            for r in rows
        ]

    def _take_snapshot(self, deployment: Deployment, broker: BrokerAPI) -> LiveSnapshot:
        account = broker.get_account_summary()
        positions = broker.get_positions()
        equity = account.get("equity", deployment.initial_cash)
        cash = account.get("cash", 0.0)
        total_pnl = equity - deployment.initial_cash
        total_trades = len(deployment.trades)
        total_fees = sum(t.commission for t in deployment.trades)

        return LiveSnapshot(
            deployment_id=deployment.id,
            timestamp=datetime.utcnow(),
            equity=equity,
            cash=cash,
            positions=positions,
            daily_pnl=0.0,  # Computed by monitor from snapshot series
            total_pnl=total_pnl,
            total_trades=total_trades,
            total_fees=total_fees,
        )

    def _get_latest_price(self, prices: dict[str, Any], symbol: str) -> float:
        df = prices.get(symbol)
        if df is None or len(df) == 0:
            return 0.0
        return float(df["Close"].iloc[-1])

    def _save_deployment(self, deployment: Deployment) -> None:
        row = {
            "id": deployment.id,
            "spec_id": deployment.spec_id,
            "account_id": deployment.account_id,
            "mode": deployment.mode,
            "status": deployment.status,
            "symbols_json": json.dumps(deployment.symbols),
            "initial_cash": deployment.initial_cash,
            "config_json": json.dumps(deployment.config),
            "started_at": deployment.started_at.isoformat(),
            "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
        }
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO deployments
                    (id, spec_id, account_id, mode, status, symbols_json,
                     initial_cash, config_json, started_at, stopped_at)
                VALUES
                    (:id, :spec_id, :account_id, :mode, :status, :symbols_json,
                     :initial_cash, :config_json, :started_at, :stopped_at)
            """), row)

    def _save_trades(self, deployment_id: str, trades: list[TradeRecord]) -> None:
        with self._engine.begin() as conn:
            for trade in trades:
                conn.execute(text("""
                    INSERT INTO trades
                        (deployment_id, symbol, side, quantity, price, commission, order_id, executed_at)
                    VALUES
                        (:deployment_id, :symbol, :side, :quantity, :price, :commission, :order_id, :executed_at)
                """), {
                    "deployment_id": deployment_id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "commission": trade.commission,
                    "order_id": trade.order_id,
                    "executed_at": trade.timestamp.isoformat(),
                })

    def _save_snapshot(self, snapshot: LiveSnapshot) -> None:
        positions_data = [
            {"symbol": p.symbol, "quantity": p.quantity,
             "avg_cost": p.avg_cost, "market_value": p.market_value}
            for p in snapshot.positions
        ]
        with self._engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO snapshots
                    (deployment_id, equity, cash, daily_pnl, total_pnl,
                     total_trades, total_fees, positions_json, recorded_at)
                VALUES
                    (:deployment_id, :equity, :cash, :daily_pnl, :total_pnl,
                     :total_trades, :total_fees, :positions_json, :recorded_at)
            """), {
                "deployment_id": snapshot.deployment_id,
                "equity": snapshot.equity,
                "cash": snapshot.cash,
                "daily_pnl": snapshot.daily_pnl,
                "total_pnl": snapshot.total_pnl,
                "total_trades": snapshot.total_trades,
                "total_fees": snapshot.total_fees,
                "positions_json": json.dumps(positions_data),
                "recorded_at": snapshot.timestamp.isoformat(),
            })
