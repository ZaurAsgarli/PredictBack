"""
FINAL SYSTEM AUDIT - Go/No-Go Decision Script
==============================================
Comprehensive verification of all system layers:
1. Census (Volume Check)
2. Deep Link Trace (Connectivity)
3. Financial Audit (Math Check)
4. Intelligence Check (ML & Security)
5. Blockchain Fidelity Check
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from backend_api.api.users.models import User
from backend_api.api.trades.models import Trade
from backend_api.api.markets.models import Market, PriceHistory, OutcomeToken
from backend_api.api.positions.models import Position
from backend_api.api.liquidity.models import LiquidityEvent
from backend_api.api.disputes.models import Dispute
from backend_api.api.indexer.models import OnchainTransaction, OnchainEventLog
from security_engine.models import SecurityLog, LoginAttempt
from ml_service.training.models import TradeRiskPrediction
from decimal import Decimal
import random


# ANSI Color Codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def passed(msg):
    return f"{Colors.GREEN}✓ PASS{Colors.RESET} - {msg}"


def failed(msg):
    return f"{Colors.RED}✗ FAIL{Colors.RESET} - {msg}"


def warning(msg):
    return f"{Colors.YELLOW}⚠ WARN{Colors.RESET} - {msg}"


def info(msg):
    return f"{Colors.CYAN}ℹ INFO{Colors.RESET} - {msg}"


class Command(BaseCommand):
    help = 'Final System Audit - Go/No-Go Decision'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log_result(self, status, category, message):
        self.results.append((status, category, message))
        if status == 'PASS':
            self.passed += 1
            self.stdout.write(passed(message))
        elif status == 'FAIL':
            self.failed += 1
            self.stdout.write(failed(message))
        else:
            self.warnings += 1
            self.stdout.write(warning(message))

    def handle(self, *args, **options):
        self.stdout.write(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")
        self.stdout.write(f"{Colors.BOLD}{Colors.BLUE}🔍 FINAL SYSTEM AUDIT - GO/NO-GO DECISION{Colors.RESET}")
        self.stdout.write(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")

        # ============================================================
        # AUDIT 1: THE CENSUS (Volume Check)
        # ============================================================
        self.stdout.write(f"\n{Colors.BOLD}[AUDIT 1] THE CENSUS - Volume Check{Colors.RESET}")
        self.stdout.write("-" * 50)

        counts = {
            'Users': (User.objects.count(), 450),
            'Trades': (Trade.objects.count(), 4000),
            'Markets': (Market.objects.count(), 80),
            'TransactionLogs': (OnchainTransaction.objects.count(), 4000),
            'SecurityLogs': (SecurityLog.objects.count(), 50),
            'UserPositions': (Position.objects.count(), 1000),
            'ContractEvents': (OnchainEventLog.objects.count(), 500),
            'PriceHistory': (PriceHistory.objects.count(), 4000),
            'LoginAttempts': (LoginAttempt.objects.count(), 100),
            'MLPredictions': (TradeRiskPrediction.objects.count(), 50),
        }

        for table, (actual, minimum) in counts.items():
            if actual >= minimum:
                self.log_result('PASS', 'CENSUS', f"{table}: {actual:,} (min: {minimum})")
            else:
                self.log_result('FAIL', 'CENSUS', f"{table}: {actual:,} < {minimum} (BELOW THRESHOLD)")

        # ============================================================
        # AUDIT 2: DEEP LINK TRACE (Connectivity Check)
        # ============================================================
        self.stdout.write(f"\n{Colors.BOLD}[AUDIT 2] DEEP LINK TRACE - Connectivity Check{Colors.RESET}")
        self.stdout.write("-" * 50)

        sample_trades = list(Trade.objects.select_related('user', 'market').order_by('?')[:5])

        for i, trade in enumerate(sample_trades):
            self.stdout.write(info(f"Tracing Trade #{trade.id}..."))

            # Check user link
            if trade.user:
                self.log_result('PASS', 'LINK', f"  Trade {trade.id} → User '{trade.user.username}'")
            else:
                self.log_result('FAIL', 'LINK', f"  Trade {trade.id} → User is NULL!")

            # Check market link
            if trade.market:
                self.log_result('PASS', 'LINK', f"  Trade {trade.id} → Market '{trade.market.title[:30]}...'")
            else:
                self.log_result('FAIL', 'LINK', f"  Trade {trade.id} → Market is NULL!")

            # Check transaction hash
            if trade.onchain_tx_hash and trade.onchain_tx_hash.startswith('0x'):
                self.log_result('PASS', 'LINK', f"  Trade {trade.id} → TX Hash: {trade.onchain_tx_hash[:20]}...")
            elif trade.onchain_tx_hash:
                self.log_result('WARN', 'LINK', f"  Trade {trade.id} → TX Hash invalid format")
            else:
                self.log_result('WARN', 'LINK', f"  Trade {trade.id} → No TX Hash (OK for legacy)")

            # Check price history exists for market
            if trade.market:
                ph_count = PriceHistory.objects.filter(market=trade.market).count()
                if ph_count > 0:
                    self.log_result('PASS', 'LINK', f"  Trade {trade.id} → {ph_count} Price History entries")
                else:
                    self.log_result('FAIL', 'LINK', f"  Trade {trade.id} → NO Price History!")

        # ============================================================
        # AUDIT 3: FINANCIAL AUDIT (Math Check)
        # ============================================================
        self.stdout.write(f"\n{Colors.BOLD}[AUDIT 3] FINANCIAL AUDIT - Math Check{Colors.RESET}")
        self.stdout.write("-" * 50)

        # Check for negative wallet balances
        # Note: wallet_balance may not exist, check total_points instead
        try:
            negative_users = User.objects.filter(total_points__lt=0).count()
            if negative_users == 0:
                self.log_result('PASS', 'FINANCE', "No users with negative points")
            else:
                self.log_result('FAIL', 'FINANCE', f"{negative_users} users have negative points!")
        except Exception as e:
            self.log_result('WARN', 'FINANCE', f"Could not check user points: {str(e)}")

        # Check market liquidity pools
        negative_markets = Market.objects.filter(liquidity_pool__lt=0).count()
        if negative_markets == 0:
            self.log_result('PASS', 'FINANCE', "No markets with negative liquidity")
        else:
            self.log_result('FAIL', 'FINANCE', f"{negative_markets} markets have negative liquidity!")

        # Check total liquidity
        total_liquidity = Market.objects.aggregate(total=Sum('liquidity_pool'))['total'] or 0
        self.stdout.write(info(f"Total Market Liquidity: ${total_liquidity:,.2f}"))
        
        if total_liquidity > 0:
            self.log_result('PASS', 'FINANCE', f"Positive liquidity pool: ${total_liquidity:,.2f}")
        else:
            self.log_result('FAIL', 'FINANCE', "Zero or negative total liquidity!")

        # Check positions have values
        positions_with_tokens = Position.objects.filter(yes_tokens__gt=0).count()
        positions_with_tokens += Position.objects.filter(no_tokens__gt=0).count()
        if positions_with_tokens > 0:
            self.log_result('PASS', 'FINANCE', f"{positions_with_tokens} positions have token holdings")
        else:
            self.log_result('WARN', 'FINANCE', "No positions with tokens found")

        # ============================================================
        # AUDIT 4: INTELLIGENCE CHECK (ML & Security)
        # ============================================================
        self.stdout.write(f"\n{Colors.BOLD}[AUDIT 4] INTELLIGENCE CHECK - ML & Security{Colors.RESET}")
        self.stdout.write("-" * 50)

        # Check blocked users
        blocked_count = User.objects.filter(role=User.Role.BLOCKED).count()
        if blocked_count >= 5:
            self.log_result('PASS', 'INTEL', f"{blocked_count} users are BLOCKED")
        else:
            self.log_result('FAIL', 'INTEL', f"Only {blocked_count} blocked users (expected >= 5)")

        # Check for auto-ban logs
        auto_ban_logs = SecurityLog.objects.filter(
            message__icontains='AUTO'
        ).count() + SecurityLog.objects.filter(
            message__icontains='BLOCKED'
        ).count()
        
        if auto_ban_logs > 0:
            self.log_result('PASS', 'INTEL', f"{auto_ban_logs} AUTO-BAN security logs found")
        else:
            self.log_result('WARN', 'INTEL', "No AUTO-BAN logs found (may be OK if no bans triggered)")

        # Check ML predictions
        high_risk_predictions = TradeRiskPrediction.objects.filter(score__gt=0.85).count()
        if high_risk_predictions > 0:
            self.log_result('PASS', 'INTEL', f"{high_risk_predictions} high-risk ML predictions")
        else:
            self.log_result('WARN', 'INTEL', "No high-risk predictions found")

        # Check login attempts
        failed_logins = LoginAttempt.objects.filter(success=False).count()
        if failed_logins > 0:
            self.log_result('PASS', 'INTEL', f"{failed_logins} failed login attempts logged")
        else:
            self.log_result('WARN', 'INTEL', "No failed login attempts (security logging may be empty)")

        # ============================================================
        # AUDIT 5: BLOCKCHAIN FIDELITY CHECK
        # ============================================================
        self.stdout.write(f"\n{Colors.BOLD}[AUDIT 5] BLOCKCHAIN FIDELITY CHECK{Colors.RESET}")
        self.stdout.write("-" * 50)

        # Disputes
        dispute_count = Dispute.objects.count()
        if dispute_count > 0:
            self.log_result('PASS', 'CHAIN', f"{dispute_count} Dispute events recorded")
        else:
            self.log_result('FAIL', 'CHAIN', "No Disputes in database!")

        # Liquidity Events
        liq_count = LiquidityEvent.objects.count()
        if liq_count > 0:
            self.log_result('PASS', 'CHAIN', f"{liq_count} Liquidity Events recorded")
        else:
            self.log_result('FAIL', 'CHAIN', "No Liquidity Events in database!")

        # Contract Events linked to Transactions
        linked_events = OnchainEventLog.objects.filter(onchain_tx__isnull=False).count()
        total_events = OnchainEventLog.objects.count()
        
        if linked_events > 0:
            link_rate = (linked_events / total_events * 100) if total_events > 0 else 0
            self.log_result('PASS', 'CHAIN', f"{linked_events}/{total_events} events linked to TX ({link_rate:.1f}%)")
        else:
            self.log_result('WARN', 'CHAIN', "No events linked to transactions")

        # Check for various event types
        event_types = OnchainEventLog.objects.values('event_name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        for et in event_types:
            self.stdout.write(info(f"  Event Type: {et['event_name']} ({et['count']} records)"))

        # ============================================================
        # FINAL VERDICT
        # ============================================================
        self.stdout.write(f"\n{Colors.BOLD}{'=' * 70}{Colors.RESET}")
        self.stdout.write(f"{Colors.BOLD}📊 AUDIT SUMMARY{Colors.RESET}")
        self.stdout.write(f"{'=' * 70}")
        
        self.stdout.write(f"{Colors.GREEN}  ✓ PASSED: {self.passed}{Colors.RESET}")
        self.stdout.write(f"{Colors.RED}  ✗ FAILED: {self.failed}{Colors.RESET}")
        self.stdout.write(f"{Colors.YELLOW}  ⚠ WARNINGS: {self.warnings}{Colors.RESET}")
        
        self.stdout.write(f"\n{'=' * 70}")
        
        if self.failed == 0:
            self.stdout.write(f"{Colors.BOLD}{Colors.GREEN}")
            self.stdout.write("██████╗ ██████╗ ███████╗███████╗███╗   ██╗")
            self.stdout.write("██╔════╝ ██╔══██╗██╔════╝██╔════╝████╗  ██║")
            self.stdout.write("██║  ███╗██████╔╝█████╗  █████╗  ██╔██╗ ██║")
            self.stdout.write("██║   ██║██╔══██╗██╔══╝  ██╔══╝  ██║╚██╗██║")
            self.stdout.write("╚██████╔╝██║  ██║███████╗███████╗██║ ╚████║")
            self.stdout.write(" ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝")
            self.stdout.write(f"{Colors.RESET}")
            self.stdout.write(f"\n{Colors.BOLD}{Colors.GREEN}🚀 SYSTEM IS GO FOR DEMO!{Colors.RESET}\n")
        else:
            self.stdout.write(f"{Colors.BOLD}{Colors.RED}")
            self.stdout.write("██████╗ ███████╗██████╗ ")
            self.stdout.write("██╔══██╗██╔════╝██╔══██╗")
            self.stdout.write("██████╔╝█████╗  ██║  ██║")
            self.stdout.write("██╔══██╗██╔══╝  ██║  ██║")
            self.stdout.write("██║  ██║███████╗██████╔╝")
            self.stdout.write("╚═╝  ╚═╝╚══════╝╚═════╝ ")
            self.stdout.write(f"{Colors.RESET}")
            self.stdout.write(f"\n{Colors.BOLD}{Colors.RED}❌ SYSTEM HAS {self.failed} CRITICAL FAILURES!{Colors.RESET}")
            self.stdout.write(f"{Colors.YELLOW}Review failures above and re-run seed scripts.{Colors.RESET}\n")
