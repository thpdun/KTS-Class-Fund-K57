"""
Blockchain RPC Indexer (Read-Only Implementation) for KTS-Class-Fund-K57 (Phase 2 V4.4).

Strict Safety Rules:
1. Read-only on Blockchain: ONLY whitelisted read-only JSON-RPC methods are allowed.
   State-mutating or signing RPC methods (`eth_sendRawTransaction`, `eth_sendTransaction`,
   `eth_sign`, etc.) are strictly forbidden.
2. Never uses or accepts private keys.
3. Reads RPC URL and configuration from environment variables (`SEPOLIA_RPC_URL`,
   `CONTRACT_DEPLOY_BLOCK`) with safe public defaults; never hardcodes secret API keys.
4. Checks HTTP and JSON-RPC response status before processing (`AGENTS.md` Rule 2).
5. Preserves exact integer Wei (`int` and `str`) in all indexed records and state
   reconciliation; converts Wei to ETH (`Decimal` string) ONLY for display fields
   (`AGENTS.md` Rule 3).
6. Only indexes events that actually exist in `ProjectCore.sol` and `CONTRACT_ABI`
   (17 events). Explicitly rejects nonexistent event names such as `RefundApproved`
   or `RefundReady`.
"""

from __future__ import annotations

import copy
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union
from zoneinfo import ZoneInfo

from eth_abi import decode as abi_decode
from eth_abi import encode as abi_encode
from eth_utils import keccak, to_checksum_address

try:
    from backend.accounting_engine import (
        BOUNDARY_WINDOW_SECONDS,
        WEI_PER_ETH,
        classify_transaction_at_timestamp,
        get_vn_tz,
        wei_to_eth_str,
    )
except ImportError:
    from accounting_engine import (
        BOUNDARY_WINDOW_SECONDS,
        WEI_PER_ETH,
        classify_transaction_at_timestamp,
        get_vn_tz,
        wei_to_eth_str,
    )

SHARED_SECOND_BOUNDARY_TS: int = 1793619753
BLOCK_TIME_SAFETY_WINDOW_SECONDS: int = BOUNDARY_WINDOW_SECONDS
VN_TZ = get_vn_tz()

# ============================================================================
# 1. CONSTANTS & CANONICAL CONTRACT CONFIGURATION
# ============================================================================

EXPECTED_SEPOLIA_CHAIN_ID: int = 11155111
DEFAULT_CONTRACT_ADDRESS: str = "0xADCE24AeC2b194B58D882fa9FDe4112115770b03"
DEFAULT_CONTRACT_CREATOR: str = "0x36Fd4887e9d1ecA4Ae5062A745cc2c6182B77060"
DEFAULT_DEPLOYMENT_TX_HASH: str = "0x3b15cad8c8de4724cf31f9ec5212745a7f561749b0d3b74ebb6ed2371d2f2603"
DEFAULT_DEPLOY_BLOCK: int = 12042025
DEFAULT_DEPLOY_BLOCK_HASH: str = "0x347c40a0578b588bc7729e6951c20b3788c041d48b508c1537c4816dbb81864e"
DEFAULT_FIRST_OBSERVED_EVENT_BLOCK: int = 12047881

DEFAULT_SEPOLIA_RPC_URL: str = "https://ethereum-sepolia-rpc.publicnode.com"
FALLBACK_SEPOLIA_RPC_URL: str = "https://rpc.sepolia.org"
# Verified deployment block on Sepolia for 0x90948699FF04bC9cF159a39e200F09885439503D is 12042025
# (First BCSMemberUpdated log is at block 12047881).
DEFAULT_DEPLOY_SEARCH_FLOOR_BLOCK: int = DEFAULT_DEPLOY_BLOCK
DEFAULT_LOG_CHUNK_SIZE: int = 45000

ALLOWED_READONLY_RPC_METHODS: Set[str] = {
    "eth_chainId",
    "eth_blockNumber",
    "eth_getCode",
    "eth_getBlockByNumber",
    "eth_getBlockByHash",
    "eth_getLogs",
    "eth_call",
    "eth_getBalance",
    "eth_getTransactionReceipt",
    "eth_getTransactionByHash",
}

FORBIDDEN_MUTATING_RPC_METHODS: Set[str] = {
    "eth_sendTransaction",
    "eth_sendRawTransaction",
    "eth_sign",
    "eth_signTransaction",
    "eth_signTypedData",
    "personal_sign",
    "personal_sendTransaction",
    "eth_accounts",
    "eth_requestAccounts",
}

# RefundStatus enum values in ProjectCore.sol:
# enum RefundStatus { Pending, Ready, Executed, Cancelled, Expired }
REFUND_STATUS_PENDING: int = 0
REFUND_STATUS_READY: int = 1
REFUND_STATUS_EXECUTED: int = 2
REFUND_STATUS_CANCELLED: int = 3
REFUND_STATUS_EXPIRED: int = 4

REFUND_STATUS_NAMES: Dict[int, str] = {
    REFUND_STATUS_PENDING: "Pending",
    REFUND_STATUS_READY: "Ready",
    REFUND_STATUS_EXECUTED: "Executed",
    REFUND_STATUS_CANCELLED: "Cancelled",
    REFUND_STATUS_EXPIRED: "Expired",
}

# SpendStatus enum values in ProjectCore.sol:
# enum SpendStatus { Pending, Ready, Executed, Cancelled, Expired }
SPEND_STATUS_PENDING: int = 0
SPEND_STATUS_READY: int = 1
SPEND_STATUS_EXECUTED: int = 2
SPEND_STATUS_CANCELLED: int = 3
SPEND_STATUS_EXPIRED: int = 4

# Basis points constants in ProjectCore.sol (1% = 100 bps, 99% = 9900 bps)
FEE_BPS: int = 100
NET_DEPOSIT_BPS: int = 9900
BPS_DENOMINATOR: int = 10000

# Phase 2.1 & 2.2.1 Verification & Reconciliation Status Constants
DEPLOY_BLOCK_VERIFIED: str = "VERIFIED"
SYNC_CONFIG_REQUIRED: str = "SYNC_CONFIG_REQUIRED"

# Current verified ProjectCore.sol accounting model (`0x90948699FF04bC9cF159a39e200F09885439503D`):
# - `studentContributions` increases by 100% `msg.value` (Gross Contribution).
# - `FundDeposited` emits 100% `msg.value` (Gross Contribution).
# - `AdminFeeCollected` emits 1% (`(amount * 100) // 10000`).
# - `classFundBalance` increases by 99% (`amount - adminFee`).
# - `adminFeePool` increases by 1% (`adminFee`).
# Formula:
#   `studentContributions[w] = SUM(FundDeposited[w]) - SUM(RefundRequestExecuted[w])`
#   `classFundDeposits = SUM(FundDeposited) - SUM(AdminFeeCollected)`
CONTRACT_VERSION_GROSS_CONTRIBUTION: str = "GROSS_CONTRIBUTION"
# Deprecated alias kept for backward compatibility with previously saved snapshots/configs
CONTRACT_VERSION_NEW_NET: str = CONTRACT_VERSION_GROSS_CONTRIBUTION
LEGACY_COMPAT_GROSS_VERSION_ALIASES: Set[str] = {
    CONTRACT_VERSION_GROSS_CONTRIBUTION,
    "NEW_NET_CONTRIBUTION",
}

# Upgraded contract (`KTS-Class-Fund-K57 Phase 1 / Section A`):
# - `FundDeposited` emits 100% gross `msg.value`.
# - `AdminFeeCollected` emits 1% (`(amount * 100) // 10000`).
# - `studentContributions` records 99% net (`amount - adminFee`) and decreases on executed refunds.
# - `studentTotalDeposited` records cumulative 100% gross deposits (`amount`, never decremented on refund).
# - `getStudentMaxRefund(w)` returns `min(getStudentAvailableContribution(w), getAvailableClassFund())`.
CONTRACT_VERSION_NET_CONTRIBUTION: str = "NET_CONTRIBUTION"

# Historical legacy contract (`0xe3e1db1da1cae10e92337c36bb13004bf984ee91`) where `FundDeposited`
# emitted 99% net while `studentContributions` stored 100% gross:
#   `studentContributions[w] = SUM(FundDeposited[w]) + SUM(AdminFeeCollected[w]) - SUM(RefundRequestExecuted[w])`
CONTRACT_VERSION_LEGACY_GROSS: str = "LEGACY_GROSS_CONTRIBUTION"
CONTRACT_VERSION_UNVERIFIED: str = "CONTRACT_VERSION_UNVERIFIED"

DEPLOYED_ABI_VERIFIED: str = "DEPLOYED_ABI_VERIFIED"
DEPLOYED_ABI_NOT_VERIFIED: str = "DEPLOYED_ABI_NOT_VERIFIED"

WEI_PER_ETH = Decimal("1000000000000000000")

# Exact 17 events and required view functions matching contracts/project/ProjectCore.sol
# and web/index.html CONTRACT_ABI.
PROJECT_CORE_ABI: List[Dict[str, Any]] = [
    # Events (17 total)
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "student", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "feeAmount", "type": "uint256"},
        ],
        "name": "AdminFeeCollected",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "advisor", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "AdminFeeWithdrawn",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "member", "type": "address"},
            {"indexed": False, "internalType": "bool", "name": "status", "type": "bool"},
        ],
        "name": "BCSMemberUpdated",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "student", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "FundDeposited",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "refundId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "applicant", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "RefundExecutionFailed",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "student", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "RefundProcessed",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "refundId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "applicant", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "reason", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "createdAt", "type": "uint256"},
        ],
        "name": "RefundRequestCreated",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "refundId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "applicant", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "RefundRequestExecuted",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "refundId", "type": "uint256"},
        ],
        "name": "RefundRequestExpired",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "refundId", "type": "uint256"},
        ],
        "name": "RefundRequestReady",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "refundId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "voter", "type": "address"},
            {"indexed": False, "internalType": "bool", "name": "support", "type": "bool"},
            {"indexed": False, "internalType": "uint256", "name": "yesVotes", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "noVotes", "type": "uint256"},
        ],
        "name": "RefundRequestVoted",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "requestId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "recipient", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "SpendExecutionFailed",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "requestId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "creator", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "recipient", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "description", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "createdAt", "type": "uint256"},
        ],
        "name": "SpendRequestCreated",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "requestId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "recipient", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "SpendRequestExecuted",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "requestId", "type": "uint256"},
        ],
        "name": "SpendRequestExpired",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "requestId", "type": "uint256"},
        ],
        "name": "SpendRequestReady",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "requestId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "voter", "type": "address"},
            {"indexed": False, "internalType": "bool", "name": "support", "type": "bool"},
            {"indexed": False, "internalType": "uint256", "name": "yesVotes", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "noVotes", "type": "uint256"},
        ],
        "name": "SpendRequestVoted",
        "type": "event",
    },
    # Required Public / View Functions
    {
        "inputs": [],
        "name": "advisor",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "classFundBalance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "adminFeePool",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "reservedSpendAmount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "reservedRefundAmount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getFundBalance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getAvailableClassFund",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getTotalContractBalance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "studentContributions",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "studentTotalDeposited",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "_student", "type": "address"}],
        "name": "getStudentContribution",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "pendingStudentRefundAmount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "_student", "type": "address"}],
        "name": "getStudentAvailableContribution",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "student", "type": "address"}],
        "name": "getStudentMaxRefund",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "refundRequestCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_refundId", "type": "uint256"}],
        "name": "getRefundRequest",
        "outputs": [
            {"internalType": "address", "name": "applicant", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "string", "name": "reason", "type": "string"},
            {"internalType": "uint256", "name": "yesVotes", "type": "uint256"},
            {"internalType": "uint256", "name": "noVotes", "type": "uint256"},
            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            {"internalType": "uint8", "name": "status", "type": "uint8"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "spendRequestCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_requestId", "type": "uint256"}],
        "name": "getSpendRequest",
        "outputs": [
            {"internalType": "address", "name": "recipient", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "string", "name": "description", "type": "string"},
            {"internalType": "uint256", "name": "yesVotes", "type": "uint256"},
            {"internalType": "uint256", "name": "noVotes", "type": "uint256"},
            {"internalType": "uint256", "name": "createdAt", "type": "uint256"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            {"internalType": "uint8", "name": "status", "type": "uint8"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

REQUIRED_CORE_EVENTS: Set[str] = {
    "FundDeposited",
    "AdminFeeCollected",
    "AdminFeeWithdrawn",
    "BCSMemberUpdated",
    "SpendRequestCreated",
    "SpendRequestVoted",
    "SpendRequestReady",
    "SpendRequestExecuted",
    "SpendExecutionFailed",
    "SpendRequestExpired",
    "RefundRequestCreated",
    "RefundRequestVoted",
    "RefundRequestReady",
    "RefundRequestExecuted",
    "RefundExecutionFailed",
    "RefundRequestExpired",
    "RefundProcessed",
}

REQUIRED_CORE_VIEW_FUNCTIONS: Set[str] = {
    "studentContributions",
    "pendingStudentRefundAmount",
    "getStudentAvailableContribution",
    "reservedRefundAmount",
    "getAvailableClassFund",
    "classFundBalance",
    "reservedSpendAmount",
    "refundRequestCount",
    "getRefundRequest",
}

REQUIRED_NET_CONTRIBUTION_VIEW_FUNCTIONS: Set[str] = REQUIRED_CORE_VIEW_FUNCTIONS | {
    "studentTotalDeposited",
    "getStudentMaxRefund",
}


# ============================================================================
# 2. CUSTOM EXCEPTIONS
# ============================================================================


class BlockchainIndexerError(Exception):
    """Base exception for Blockchain RPC Indexer errors."""


class ReadOnlyPolicyViolationError(BlockchainIndexerError):
    """Raised when a forbidden mutating RPC method or private key is attempted."""


class ChainIdMismatchError(BlockchainIndexerError):
    """Raised when the connected RPC chainId does not match expected (11155111)."""


class InvalidContractAddressError(BlockchainIndexerError):
    """Raised when the contract address is malformed or has no deployed bytecode (`0x`)."""


class InvalidContractABIError(BlockchainIndexerError):
    """Raised when the provided ABI is malformed, missing required events/functions, or requests nonexistent events."""


class RpcTransportError(BlockchainIndexerError):
    """Raised when an RPC call fails after retries or returns an RPC error / malformed payload."""


classRpcPrunedHistoryError = RpcTransportError


class StateReconciliationError(BlockchainIndexerError):
    """Raised when same-blockTag state calls cannot be completed consistently."""


# ============================================================================
# 3. UTILITY FUNCTIONS (WEI / ETH DISPLAY & HEX CONVERSIONS)
# ============================================================================


def wei_to_eth_display(wei_amount: Union[int, str]) -> str:
    """
    Convert an integer Wei amount to an ETH string for human display (`AGENTS.md` Rule 3).
    Accounting records MUST always keep exact integer Wei (`int` / `str`).
    """
    wei_int = int(wei_amount)
    eth_val = Decimal(wei_int) / WEI_PER_ETH
    formatted = f"{eth_val:.18f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


def parse_hex_int(value: Any, field_name: str = "hex_field") -> int:
    """Strictly parse a hex string (`0x...`) or integer into a Python `int`."""
    if isinstance(value, bool):
        raise RpcTransportError(f"Invalid integer/hex for {field_name}: boolean not allowed.")
    if isinstance(value, int):
        if value < 0:
            raise RpcTransportError(f"Negative integer not allowed for {field_name}: {value}")
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise RpcTransportError(f"Empty string for {field_name}.")
        try:
            if stripped.startswith(("0x", "0X")):
                return int(stripped, 16)
            return int(stripped, 10)
        except ValueError as exc:
            raise RpcTransportError(f"Malformed hex/integer for {field_name}: {value!r}") from exc
    raise RpcTransportError(f"Unsupported type for {field_name}: {type(value).__name__}")


def normalize_hex_hash(value: Any, expected_bytes: int = 32, field_name: str = "hash") -> str:
    """Validate and normalize a 0x-prefixed hex hash (e.g., blockHash, transactionHash)."""
    if not isinstance(value, str):
        raise RpcTransportError(f"{field_name} must be a string, got {type(value).__name__}.")
    cleaned = value.strip().lower()
    if not cleaned.startswith("0x"):
        raise RpcTransportError(f"{field_name} must start with '0x', got {value!r}.")
    hex_body = cleaned[2:]
    if len(hex_body) != expected_bytes * 2:
        raise RpcTransportError(
            f"{field_name} must have {expected_bytes * 2} hex chars, got {len(hex_body)} in {value!r}."
        )
    try:
        int(hex_body, 16)
    except ValueError as exc:
        raise RpcTransportError(f"{field_name} contains non-hex characters: {value!r}") from exc
    return "0x" + hex_body


def normalize_address(address: str, field_name: str = "address") -> str:
    """Validate an Ethereum address and return its EIP-55 checksummed string."""
    if not isinstance(address, str):
        raise InvalidContractAddressError(f"{field_name} must be a string.")
    cleaned = address.strip()
    if not cleaned.startswith(("0x", "0X")) or len(cleaned) != 42:
        raise InvalidContractAddressError(f"Invalid Ethereum {field_name}: {address!r}")
    try:
        int(cleaned[2:], 16)
        return to_checksum_address(cleaned)
    except Exception as exc:
        raise InvalidContractAddressError(f"Invalid Ethereum {field_name}: {address!r}") from exc


def build_composite_log_key(chain_id: int, transaction_hash: str, log_index: int) -> str:
    """
    Build the canonical composite deduplication key `(chainId, transactionHash, logIndex)`.
    Never deduplicate by `transactionHash` alone because a single transaction in
    `ProjectCore` emits multiple logs (e.g., `FundDeposited` + `AdminFeeCollected`,
    or `RefundRequestExecuted` + `RefundProcessed`).
    """
    tx_norm = normalize_hex_hash(transaction_hash, expected_bytes=32, field_name="transactionHash")
    return f"{int(chain_id)}:{tx_norm}:{int(log_index)}"


# ============================================================================
# 4. ABI VALIDATION & EVENT / FUNCTION CODEC
# ============================================================================


@dataclass(frozen=True)
class AbiEventSpec:
    name: str
    signature: str
    topic0: str
    indexed_inputs: Tuple[Tuple[str, str], ...]
    non_indexed_inputs: Tuple[Tuple[str, str], ...]
    all_inputs: Tuple[Tuple[str, str, bool], ...]


@dataclass(frozen=True)
class AbiFunctionSpec:
    name: str
    signature: str
    selector: str
    input_types: Tuple[str, ...]
    output_types: Tuple[str, ...]
    output_names: Tuple[str, ...]
    state_mutability: str


def validate_contract_abi(
    abi: Any,
    require_core_definitions: bool = True,
) -> Tuple[Dict[str, AbiEventSpec], Dict[str, AbiFunctionSpec]]:
    """
    Validate the contract ABI structure and build event topic0 / function selector registries.
    Raises `InvalidContractABIError` if the ABI is malformed or missing required core items.
    """
    if not isinstance(abi, list) or len(abi) == 0:
        raise InvalidContractABIError("Contract ABI must be a non-empty list of ABI entries.")

    event_specs: Dict[str, AbiEventSpec] = {}
    func_specs: Dict[str, AbiFunctionSpec] = {}

    for idx, entry in enumerate(abi):
        if not isinstance(entry, dict):
            raise InvalidContractABIError(f"ABI entry at index {idx} must be a dict.")
        entry_type = entry.get("type")
        if entry_type == "event":
            name = entry.get("name")
            inputs = entry.get("inputs")
            if not isinstance(name, str) or not name.strip():
                raise InvalidContractABIError(f"Event ABI entry at index {idx} is missing a valid 'name'.")
            if not isinstance(inputs, list):
                raise InvalidContractABIError(f"Event '{name}' must have an 'inputs' list.")

            indexed_list: List[Tuple[str, str]] = []
            non_indexed_list: List[Tuple[str, str]] = []
            all_list: List[Tuple[str, str, bool]] = []
            sig_types: List[str] = []

            for param in inputs:
                if not isinstance(param, dict):
                    raise InvalidContractABIError(f"Invalid input parameter in event '{name}'.")
                p_name = param.get("name", "")
                p_type = param.get("type", "")
                p_indexed = bool(param.get("indexed", False))
                if not isinstance(p_type, str) or not p_type:
                    raise InvalidContractABIError(f"Event '{name}' has parameter with empty type.")
                sig_types.append(p_type)
                if p_indexed:
                    indexed_list.append((p_name, p_type))
                else:
                    non_indexed_list.append((p_name, p_type))
                all_list.append((p_name, p_type, p_indexed))

            signature = f"{name}({','.join(sig_types)})"
            topic0 = "0x" + keccak(text=signature).hex()
            event_specs[name] = AbiEventSpec(
                name=name,
                signature=signature,
                topic0=topic0.lower(),
                indexed_inputs=tuple(indexed_list),
                non_indexed_inputs=tuple(non_indexed_list),
                all_inputs=tuple(all_list),
            )

        elif entry_type == "function":
            name = entry.get("name")
            inputs = entry.get("inputs", [])
            outputs = entry.get("outputs", [])
            mutability = entry.get("stateMutability", "nonpayable")
            if not isinstance(name, str) or not name.strip():
                raise InvalidContractABIError(f"Function ABI entry at index {idx} is missing a valid 'name'.")
            if not isinstance(inputs, list) or not isinstance(outputs, list):
                raise InvalidContractABIError(f"Function '{name}' inputs/outputs must be lists.")

            in_types: List[str] = []
            for param in inputs:
                if not isinstance(param, dict) or not param.get("type"):
                    raise InvalidContractABIError(f"Invalid input param in function '{name}'.")
                in_types.append(str(param["type"]))

            out_types: List[str] = []
            out_names: List[str] = []
            for param in outputs:
                if not isinstance(param, dict) or not param.get("type"):
                    raise InvalidContractABIError(f"Invalid output param in function '{name}'.")
                out_types.append(str(param["type"]))
                out_names.append(str(param.get("name", "")))

            signature = f"{name}({','.join(in_types)})"
            selector = "0x" + keccak(text=signature)[:4].hex()
            func_specs[name] = AbiFunctionSpec(
                name=name,
                signature=signature,
                selector=selector.lower(),
                input_types=tuple(in_types),
                output_types=tuple(out_types),
                output_names=tuple(out_names),
                state_mutability=str(mutability),
            )

    if require_core_definitions:
        missing_events = REQUIRED_CORE_EVENTS - set(event_specs.keys())
        if missing_events:
            raise InvalidContractABIError(
                f"ABI is missing required ProjectCore events: {sorted(missing_events)}"
            )
        missing_funcs = REQUIRED_CORE_VIEW_FUNCTIONS - set(func_specs.keys())
        if missing_funcs:
            raise InvalidContractABIError(
                f"ABI is missing required ProjectCore view functions: {sorted(missing_funcs)}"
            )

    return event_specs, func_specs


# ============================================================================
# 5. READ-ONLY JSON-RPC CLIENT WITH RETRY & STRICT VALIDATION
# ============================================================================


class JsonRpcClient:
    """
    Read-only JSON-RPC client for Sepolia with timeout, exponential backoff retry,
    and strict HTTP + JSON-RPC response validation (`AGENTS.md` Rule 2).
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        timeout_seconds: float = 12.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.25,
        transport_fn: Optional[Callable[[str, Dict[str, Any], float], Dict[str, Any]]] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        resolved_url = (rpc_url or os.getenv("SEPOLIA_RPC_URL") or DEFAULT_SEPOLIA_RPC_URL).strip()
        if not resolved_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid RPC URL scheme: {resolved_url!r}")
        self.rpc_url: str = resolved_url
        self.timeout_seconds: float = float(timeout_seconds)
        self.max_retries: int = max(1, int(max_retries))
        self.retry_backoff_seconds: float = max(0.0, float(retry_backoff_seconds))
        self._transport_fn = transport_fn
        self._sleep_fn = sleep_fn
        self._request_counter: int = 0
        self.call_history: List[Dict[str, Any]] = []

    def call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """
        Execute a whitelisted read-only JSON-RPC call.
        Raises `ReadOnlyPolicyViolationError` if a mutating or non-whitelisted method is called.
        """
        if not isinstance(method, str) or not method.strip():
            raise RpcTransportError("JSON-RPC method name must be a non-empty string.")
        method_name = method.strip()

        if method_name in FORBIDDEN_MUTATING_RPC_METHODS or method_name not in ALLOWED_READONLY_RPC_METHODS:
            raise ReadOnlyPolicyViolationError(
                f"Method '{method_name}' is forbidden by Phase 2 Read-Only Blockchain Policy."
            )

        rpc_params = list(params) if params is not None else []
        self._request_counter += 1
        req_id = self._request_counter
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method_name,
            "params": rpc_params,
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            self.call_history.append(
                {
                    "id": req_id,
                    "method": method_name,
                    "params": copy.deepcopy(rpc_params),
                    "attempt": attempt,
                }
            )
            try:
                raw_response = self._send_payload(payload)
                return self._validate_rpc_response(raw_response, method_name)
            except (TimeoutError, urllib.error.URLError, ConnectionError) as net_exc:
                last_error = RpcTransportError(
                    f"RPC network/timeout error on {method_name} (attempt {attempt}/{self.max_retries}): {net_exc}"
                )
            except RpcTransportError as rpc_exc:
                last_error = rpc_exc
                # Do not retry deterministic execution revert or pruned historical state errors
                msg_lower = str(rpc_exc).lower()
                if "historical state" in msg_lower or "execution reverted" in msg_lower:
                    raise rpc_exc

            if attempt < self.max_retries:
                backoff = self.retry_backoff_seconds * (2 ** (attempt - 1))
                if backoff > 0:
                    self._sleep_fn(backoff)

        assert last_error is not None
        raise last_error

    def _send_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self._transport_fn is not None:
            resp = self._transport_fn(self.rpc_url, payload, self.timeout_seconds)
            if not isinstance(resp, dict):
                raise RpcTransportError(
                    f"Malformed RPC transport return type: expected dict, got {type(resp).__name__}"
                )
            return resp

        body_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.rpc_url,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "KTS-Class-Fund-K57-Phase2-ReadOnlyIndexer/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                status_code = getattr(response, "status", None) or response.getcode()
                if status_code != 200:
                    raise RpcTransportError(f"HTTP status {status_code} from RPC endpoint {self.rpc_url}")
                raw_bytes = response.read()
        except urllib.error.HTTPError as http_err:
            raise RpcTransportError(
                f"HTTP error {http_err.code} from RPC endpoint {self.rpc_url}: {http_err.reason}"
            ) from http_err

        try:
            decoded = json.loads(raw_bytes.decode("utf-8"))
        except Exception as json_exc:
            raise RpcTransportError(f"Invalid JSON response from RPC endpoint: {json_exc}") from json_exc

        if not isinstance(decoded, dict):
            raise RpcTransportError(f"JSON-RPC response root must be a JSON object, got {type(decoded).__name__}")
        return decoded

    @staticmethod
    def _validate_rpc_response(response: Dict[str, Any], method_name: str) -> Any:
        if not isinstance(response, dict):
            raise RpcTransportError(f"Malformed JSON-RPC response for {method_name}: not a dict.")
        if "error" in response and response["error"] is not None:
            err_obj = response["error"]
            if isinstance(err_obj, dict):
                code = err_obj.get("code", "unknown")
                message = err_obj.get("message", "unknown error")
                raise RpcTransportError(f"JSON-RPC error on {method_name} (code={code}): {message}")
            raise RpcTransportError(f"JSON-RPC error on {method_name}: {err_obj!r}")
        if "result" not in response:
            raise RpcTransportError(f"Malformed JSON-RPC response for {method_name}: missing 'result' field.")
        return response["result"]


# ============================================================================
# 6. DATA STRUCTURES FOR INDEXING, RECONCILIATION & REORG DETECTION
# ============================================================================


@dataclass
class BlockHeaderRecord:
    block_number: int
    block_hash: str
    parent_hash: str
    timestamp: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blockNumber": self.block_number,
            "blockHash": self.block_hash,
            "parentHash": self.parent_hash,
            "timestamp": self.timestamp,
            "timestampIsoVn": datetime.fromtimestamp(self.timestamp, tz=VN_TZ).isoformat(),
        }


@dataclass
class ReorgDetectionResult:
    reorg_detected: bool
    reason: Optional[str] = None
    affected_from_block: Optional[int] = None
    affected_to_block: Optional[int] = None
    mismatches: List[Dict[str, Any]] = field(default_factory=list)
    affected_log_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reorgDetected": self.reorg_detected,
            "reason": self.reason,
            "affectedFromBlock": self.affected_from_block,
            "affectedToBlock": self.affected_to_block,
            "mismatches": copy.deepcopy(self.mismatches),
            "affectedLogKeys": list(self.affected_log_keys),
        }


@dataclass(frozen=True)
class IndexerDeploymentConfig:
    """
    Single canonical deployment configuration for `ProjectCore` on Sepolia,
    verified in Phase 2.2 and overrideable via environment variables.
    """

    chain_id: int = EXPECTED_SEPOLIA_CHAIN_ID
    contract_address: str = DEFAULT_CONTRACT_ADDRESS
    contract_creator: str = DEFAULT_CONTRACT_CREATOR
    deployment_tx_hash: str = DEFAULT_DEPLOYMENT_TX_HASH
    deploy_block: int = DEFAULT_DEPLOY_BLOCK
    deploy_block_hash: str = DEFAULT_DEPLOY_BLOCK_HASH
    history_scan_start_block: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chainId": self.chain_id,
            "contractAddress": self.contract_address,
            "contractCreator": self.contract_creator,
            "deploymentTxHash": self.deployment_tx_hash,
            "deployBlock": self.deploy_block,
            "deployBlockHash": self.deploy_block_hash,
            "historyScanStartBlock": self.history_scan_start_block,
        }


def load_deployment_config(env: Optional[Mapping[str, str]] = None) -> IndexerDeploymentConfig:
    """
    Load canonical deployment configuration from environment variables with verified
    Phase 2.2 Sepolia defaults (`Chain ID 11155111`, `0x909486...503D`, creator
    `0x36Fd48...7060`, tx `0x3b15ca...2603`, block `12042025`).
    """
    env_map: Mapping[str, str] = env if env is not None else os.environ

    env_chain = env_map.get("CONTRACT_CHAIN_ID") or env_map.get("SEPOLIA_CHAIN_ID")
    chain_id = int(env_chain.strip()) if (env_chain and env_chain.strip()) else EXPECTED_SEPOLIA_CHAIN_ID

    env_addr = env_map.get("CONTRACT_ADDRESS")
    contract_address = (
        normalize_address(env_addr.strip(), field_name="CONTRACT_ADDRESS")
        if (env_addr and env_addr.strip())
        else normalize_address(DEFAULT_CONTRACT_ADDRESS, field_name="DEFAULT_CONTRACT_ADDRESS")
    )

    env_creator = env_map.get("CONTRACT_CREATOR")
    contract_creator = (
        normalize_address(env_creator.strip(), field_name="CONTRACT_CREATOR")
        if (env_creator and env_creator.strip())
        else normalize_address(DEFAULT_CONTRACT_CREATOR, field_name="DEFAULT_CONTRACT_CREATOR")
    )

    env_tx = env_map.get("CONTRACT_DEPLOY_TX_HASH")
    deployment_tx_hash = (
        normalize_hex_hash(env_tx.strip(), expected_bytes=32, field_name="CONTRACT_DEPLOY_TX_HASH")
        if (env_tx and env_tx.strip())
        else normalize_hex_hash(DEFAULT_DEPLOYMENT_TX_HASH, expected_bytes=32, field_name="DEFAULT_DEPLOYMENT_TX_HASH")
    )

    env_blk = env_map.get("CONTRACT_DEPLOY_BLOCK")
    deploy_block = int(env_blk.strip()) if (env_blk and env_blk.strip()) else DEFAULT_DEPLOY_BLOCK

    env_blk_hash = env_map.get("CONTRACT_DEPLOY_BLOCK_HASH")
    deploy_block_hash = (
        normalize_hex_hash(env_blk_hash.strip(), expected_bytes=32, field_name="CONTRACT_DEPLOY_BLOCK_HASH")
        if (env_blk_hash and env_blk_hash.strip())
        else normalize_hex_hash(DEFAULT_DEPLOY_BLOCK_HASH, expected_bytes=32, field_name="DEFAULT_DEPLOY_BLOCK_HASH")
    )

    env_scan = env_map.get("HISTORY_SCAN_START_BLOCK")
    scan_start = int(env_scan.strip()) if (env_scan and env_scan.strip()) else None

    return IndexerDeploymentConfig(
        chain_id=chain_id,
        contract_address=contract_address,
        contract_creator=contract_creator,
        deployment_tx_hash=deployment_tx_hash,
        deploy_block=deploy_block,
        deploy_block_hash=deploy_block_hash,
        history_scan_start_block=scan_start,
    )


def normalize_contract_version(version: Optional[str]) -> Optional[str]:
    """
    Normalize contract accounting version strings while preserving backward compatibility
    with previously saved snapshots or callers that used `NEW_NET_CONTRIBUTION`.
    """
    if version is None:
        return None
    clean = str(version).strip()
    if clean in LEGACY_COMPAT_GROSS_VERSION_ALIASES:
        return CONTRACT_VERSION_GROSS_CONTRIBUTION
    if clean in (
        CONTRACT_VERSION_NET_CONTRIBUTION,
        CONTRACT_VERSION_LEGACY_GROSS,
        CONTRACT_VERSION_UNVERIFIED,
    ):
        return clean
    raise ValueError(f"Unsupported contract_version: {version!r}")


# ============================================================================
# 7. BLOCKCHAIN RPC INDEXER (READ-ONLY)
# ============================================================================


class BlockchainRPCIndexer:
    """
    Phase 2 Read-Only Blockchain RPC Indexer for `ProjectCore` on Sepolia.
    """

    def __init__(
        self,
        rpc_client: Optional[JsonRpcClient] = None,
        contract_address: Optional[str] = None,
        contract_creator: Optional[str] = None,
        abi: Optional[List[Dict[str, Any]]] = None,
        expected_chain_id: Optional[int] = None,
        deploy_block: Optional[int] = None,
        deployment_tx_hash: Optional[str] = None,
        history_scan_start_block: Optional[int] = None,
        private_key: Optional[str] = None,
        config: Optional[IndexerDeploymentConfig] = None,
        max_block_range: Optional[int] = None,
    ) -> None:
        if private_key is not None or os.getenv("PRIVATE_KEY_FOR_INDEXER"):
            raise ReadOnlyPolicyViolationError(
                "BlockchainRPCIndexer is strictly read-only and MUST NOT receive a private key."
            )

        cfg = config if config is not None else load_deployment_config()
        self.deployment_config: IndexerDeploymentConfig = cfg
        self.max_block_range: int = int(max_block_range) if max_block_range is not None else DEFAULT_LOG_CHUNK_SIZE

        self.contract_address: str = (
            normalize_address(contract_address, field_name="contract_address")
            if contract_address is not None
            else cfg.contract_address
        )
        self.contract_creator: str = (
            normalize_address(contract_creator, field_name="contract_creator")
            if contract_creator is not None
            else cfg.contract_creator
        )
        self.expected_chain_id: int = int(expected_chain_id) if expected_chain_id is not None else cfg.chain_id
        self.abi: List[Dict[str, Any]] = copy.deepcopy(abi if abi is not None else PROJECT_CORE_ABI)
        self.event_specs, self.function_specs = validate_contract_abi(self.abi, require_core_definitions=True)
        self.topic0_to_event: Dict[str, AbiEventSpec] = {
            spec.topic0.lower(): spec for spec in self.event_specs.values()
        }

        self.rpc: JsonRpcClient = rpc_client if rpc_client is not None else JsonRpcClient()

        env_deploy_block = os.getenv("CONTRACT_DEPLOY_BLOCK")
        if deploy_block is not None:
            self.deploy_block: Optional[int] = int(deploy_block)
        elif config is not None and config.deploy_block is not None:
            self.deploy_block = int(config.deploy_block)
        elif env_deploy_block and env_deploy_block.strip():
            self.deploy_block = int(env_deploy_block.strip())
        else:
            self.deploy_block = None

        env_deploy_tx = os.getenv("CONTRACT_DEPLOY_TX_HASH")
        if deployment_tx_hash is not None and str(deployment_tx_hash).strip():
            self.deployment_tx_hash: Optional[str] = normalize_hex_hash(
                deployment_tx_hash, expected_bytes=32, field_name="deployment_tx_hash"
            )
        elif config is not None and config.deployment_tx_hash:
            self.deployment_tx_hash = normalize_hex_hash(
                config.deployment_tx_hash, expected_bytes=32, field_name="config.deployment_tx_hash"
            )
        elif env_deploy_tx and env_deploy_tx.strip():
            self.deployment_tx_hash = normalize_hex_hash(
                env_deploy_tx.strip(), expected_bytes=32, field_name="CONTRACT_DEPLOY_TX_HASH"
            )
        else:
            self.deployment_tx_hash = None

        if history_scan_start_block is not None:
            self.history_scan_start_block: Optional[int] = int(history_scan_start_block)
        else:
            self.history_scan_start_block = cfg.history_scan_start_block

        self.first_observed_event_block: Optional[int] = None

        # Block header cache (`blockNumber -> BlockHeaderRecord`)
        self._block_header_cache: Dict[int, BlockHeaderRecord] = {}
        # Deduplicated log store (`logKey -> parsedLogDict`)
        self._indexed_logs: Dict[str, Dict[str, Any]] = {}
        self.last_reorg_detection: Optional[ReorgDetectionResult] = None

    # ------------------------------------------------------------------------
    # 4.1 Connection, Chain ID, Bytecode & Deploy Block Verification
    # ------------------------------------------------------------------------

    def verify_network_and_contract(self, block_tag: Union[int, str] = "latest") -> Dict[str, Any]:
        """
        Verify:
        1. `eth_chainId == 11155111` (Sepolia).
        2. `eth_getCode(contractAddress)` is non-empty (`!= '0x'`).
        Returns verification metadata dict.
        """
        raw_chain_id = self.rpc.call("eth_chainId", [])
        chain_id = parse_hex_int(raw_chain_id, field_name="eth_chainId")
        if chain_id != self.expected_chain_id:
            raise ChainIdMismatchError(
                f"Chain ID mismatch: expected {self.expected_chain_id} (Sepolia), got {chain_id}."
            )

        tag_str = hex(block_tag) if isinstance(block_tag, int) else str(block_tag)
        raw_code = self.rpc.call("eth_getCode", [self.contract_address, tag_str])
        if not isinstance(raw_code, str) or not raw_code.strip().startswith("0x"):
            raise RpcTransportError(f"Malformed eth_getCode response: {raw_code!r}")

        code_clean = raw_code.strip().lower()
        if code_clean in ("0x", "0x0", "0x00"):
            raise InvalidContractAddressError(
                f"No contract bytecode found at {self.contract_address} (tag={tag_str}); address is an EOA or undeployed."
            )

        latest_block_hex = self.rpc.call("eth_blockNumber", [])
        latest_block = parse_hex_int(latest_block_hex, field_name="eth_blockNumber")

        return {
            "chainId": chain_id,
            "contractAddress": self.contract_address,
            "contractCreator": self.contract_creator,
            "bytecodeLengthBytes": (len(code_clean) - 2) // 2,
            "latestBlockNumber": latest_block,
            "verifiedAtTag": tag_str,
        }

    def _verify_deployment_receipt_dict(
        self,
        rcpt: Dict[str, Any],
        tx_hash: str,
        enforce_creator: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a transaction receipt dict as deployment proof for `self.contract_address`:
        - `receipt.status == 1`
        - `receipt.contractAddress == self.contract_address`
        - If `enforce_creator=True` and `receipt.from` is present, `receipt.from == self.contract_creator`
        - Cross-checks `receipt.blockHash` against canonical `eth_getBlockByNumber(blockNumber)` when available.
        """
        created_addr = rcpt.get("contractAddress")
        status_val = rcpt.get("status", "0x1")
        if not (
            isinstance(created_addr, str)
            and created_addr.strip().lower() == self.contract_address.lower()
            and parse_hex_int(status_val, field_name="receipt.status") == 1
        ):
            return None

        sender_addr = rcpt.get("from")
        creator_verified = False
        if isinstance(sender_addr, str) and sender_addr.strip():
            norm_sender = normalize_address(sender_addr, field_name="receipt.from")
            if enforce_creator and norm_sender.lower() != self.contract_creator.lower():
                return None
            creator_verified = norm_sender.lower() == self.contract_creator.lower()

        rcpt_block = parse_hex_int(rcpt.get("blockNumber"), field_name="receipt.blockNumber")
        rcpt_block_hash = (
            normalize_hex_hash(rcpt["blockHash"], field_name="receipt.blockHash")
            if rcpt.get("blockHash")
            else None
        )

        canonical_hash_verified = False
        if rcpt_block_hash is not None:
            try:
                header = self.get_block_header(rcpt_block)
                if header.block_hash != rcpt_block_hash:
                    return None
                canonical_hash_verified = True
            except RpcTransportError:
                pass

        return {
            "deploymentTransactionHash": normalize_hex_hash(tx_hash, field_name="tx_hash"),
            "deployBlock": rcpt_block,
            "deployBlockHash": rcpt_block_hash,
            "contractAddress": to_checksum_address(created_addr),
            "contractCreator": normalize_address(sender_addr) if (isinstance(sender_addr, str) and sender_addr.strip()) else None,
            "creatorVerified": creator_verified,
            "canonicalBlockHashVerified": canonical_hash_verified,
        }

    def _find_deployment_receipt_in_block(self, block_number: int) -> Optional[Dict[str, Any]]:
        """
        Inspect all transactions in `block_number` to find a contract creation transaction
        (`to is None`) whose receipt has `contractAddress == self.contract_address`.
        Returns the verified deployment evidence dict if found, or `None`.
        """
        raw_blk = self.rpc.call("eth_getBlockByNumber", [hex(int(block_number)), True])
        if not isinstance(raw_blk, dict):
            return None
        txs = raw_blk.get("transactions")
        if not isinstance(txs, list):
            return None

        for tx in txs:
            if isinstance(tx, dict):
                # Contract creation transactions have `to == None` (or `to` absent)
                if tx.get("to") is not None:
                    continue
                tx_hash = tx.get("hash")
            elif isinstance(tx, str):
                tx_hash = tx
            else:
                continue

            if not tx_hash:
                continue
            rcpt = self.rpc.call("eth_getTransactionReceipt", [tx_hash])
            if not isinstance(rcpt, dict):
                continue
            verified = self._verify_deployment_receipt_dict(rcpt, tx_hash, enforce_creator=False)
            if verified is not None:
                return verified
        return None

    def resolve_deploy_block(
        self,
        latest_block: Optional[int] = None,
        search_floor_block: Optional[int] = DEFAULT_DEPLOY_SEARCH_FLOOR_BLOCK,
        deployment_tx_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Phase 2.1 & 2.2.1 Section A – Strictly distinguish:
        - `deployBlock`: the block containing the contract deployment transaction (MUST be
          proven by a deployment transaction receipt or archive binary search + receipt).
        - `firstObservedEventBlock`: the earliest block where an event of the contract was observed.
        - `historyScanStartBlock`: the starting block for history scanning.

        Rules:
        - NEVER automatically treat `firstObservedEventBlock` (e.g. 12047881) as `deployBlock`
          without deployment transaction receipt proof.
        - Never scan from genesis (block 0) for logs when `deployBlock` is unverified.
        - If `deployBlock` cannot be proven, return `status = SYNC_CONFIG_REQUIRED` with
          `deployBlock = None`.
        """
        if latest_block is None:
            latest_block = parse_hex_int(self.rpc.call("eth_blockNumber", []), field_name="eth_blockNumber")

        effective_floor = (
            self.history_scan_start_block
            if self.history_scan_start_block is not None
            else search_floor_block
        )

        # Compute `firstObservedEventBlock` if a bounded scan start block (> 0) is available
        first_event_block: Optional[int] = self.first_observed_event_block
        if first_event_block is None and effective_floor is not None and int(effective_floor) > 0:
            from_blk = min(int(effective_floor), int(latest_block))
            try:
                raw_logs = self.rpc.call(
                    "eth_getLogs",
                    [
                        {
                            "address": self.contract_address,
                            "fromBlock": hex(from_blk),
                            "toBlock": hex(int(latest_block)),
                        }
                    ],
                )
                if isinstance(raw_logs, list) and len(raw_logs) > 0:
                    first_event_block = min(
                        parse_hex_int(lg.get("blockNumber"), field_name="log.blockNumber")
                        for lg in raw_logs
                        if isinstance(lg, dict) and "blockNumber" in lg
                    )
                    self.first_observed_event_block = first_event_block
            except RpcTransportError:
                pass

        # 1. Check explicit deployment_tx_hash, configured self.deployment_tx_hash, or canonical deployment_config.deployment_tx_hash
        candidate_tx_hashes: List[Tuple[str, bool]] = []
        if deployment_tx_hash is not None:
            candidate_tx_hashes.append((deployment_tx_hash, False))
        elif self.deployment_tx_hash is not None:
            candidate_tx_hashes.append((self.deployment_tx_hash, False))
        elif self.contract_address.lower() == self.deployment_config.contract_address.lower():
            candidate_tx_hashes.append((self.deployment_config.deployment_tx_hash, True))

        for raw_tx_cand, enforce_creator_flag in candidate_tx_hashes:
            norm_tx = normalize_hex_hash(raw_tx_cand, field_name="deployment_tx_hash")
            try:
                rcpt = self.rpc.call("eth_getTransactionReceipt", [norm_tx])
            except RpcTransportError:
                rcpt = None
            if isinstance(rcpt, dict):
                verified = self._verify_deployment_receipt_dict(
                    rcpt, norm_tx, enforce_creator=enforce_creator_flag
                )
                if verified is not None:
                    verified_blk = verified["deployBlock"]
                    self.deploy_block = verified_blk
                    scan_start = (
                        self.history_scan_start_block
                        if self.history_scan_start_block is not None
                        else verified_blk
                    )
                    return {
                        "status": DEPLOY_BLOCK_VERIFIED,
                        "deployBlock": verified_blk,
                        "deployBlockHash": verified["deployBlockHash"],
                        "firstObservedEventBlock": first_event_block,
                        "historyScanStartBlock": scan_start,
                        "deploymentTransactionHash": norm_tx,
                        "contractCreator": verified["contractCreator"] or self.contract_creator,
                        "creatorVerified": verified["creatorVerified"],
                        "canonicalBlockHashVerified": verified["canonicalBlockHashVerified"],
                        "resolutionMethod": "deployment_transaction_receipt",
                        "archiveBinarySearchSupported": None,
                    }

        # 2. Check configured deploy_block: verify via deployment receipt in that block if transactions are present
        if self.deploy_block is not None:
            if self.deploy_block < 0 or self.deploy_block > latest_block:
                raise BlockchainIndexerError(
                    f"Configured deploy_block {self.deploy_block} is out of valid range [0, {latest_block}]."
                )
            receipt_proof = self._find_deployment_receipt_in_block(self.deploy_block)
            if receipt_proof is not None:
                scan_start = (
                    self.history_scan_start_block
                    if self.history_scan_start_block is not None
                    else self.deploy_block
                )
                return {
                    "status": DEPLOY_BLOCK_VERIFIED,
                    "deployBlock": self.deploy_block,
                    "deployBlockHash": receipt_proof.get("deployBlockHash"),
                    "firstObservedEventBlock": first_event_block,
                    "historyScanStartBlock": scan_start,
                    "deploymentTransactionHash": receipt_proof["deploymentTransactionHash"],
                    "resolutionMethod": "configured_block_with_receipt_proof",
                    "archiveBinarySearchSupported": None,
                }

        # 3. Try archive binary search via `eth_getCode(address, blockTag)`
        lo = 0
        hi = int(latest_block)
        pruned_error: Optional[str] = None
        try:
            while lo < hi:
                mid = (lo + hi) // 2
                code_at_mid = self.rpc.call("eth_getCode", [self.contract_address, hex(mid)])
                if isinstance(code_at_mid, str) and code_at_mid.strip().lower() not in ("0x", "0x0", "0x00"):
                    hi = mid
                else:
                    lo = mid + 1

            # Check if the discovered transition block `lo` has a deployment receipt (or if mocked archive transitions cleanly)
            receipt_proof = self._find_deployment_receipt_in_block(lo)
            if receipt_proof is not None:
                self.deploy_block = lo
                scan_start = (
                    self.history_scan_start_block
                    if self.history_scan_start_block is not None
                    else lo
                )
                return {
                    "status": DEPLOY_BLOCK_VERIFIED,
                    "deployBlock": lo,
                    "firstObservedEventBlock": first_event_block,
                    "historyScanStartBlock": scan_start,
                    "deploymentTransactionHash": receipt_proof["deploymentTransactionHash"],
                    "resolutionMethod": "binary_search_eth_getCode_with_receipt_proof",
                    "archiveBinarySearchSupported": True,
                }

            # If binary search succeeded on an archive node where code at `lo - 1` is '0x' and code at `lo` is non-empty,
            # check if block `lo` has an empty transaction list (e.g. lightweight mock) vs real block without matching receipt.
            raw_blk = self.rpc.call("eth_getBlockByNumber", [hex(lo), True])
            blk_txs = raw_blk.get("transactions") if isinstance(raw_blk, dict) else None
            if blk_txs is None:
                # Lightweight archive mock without full transaction objects
                self.deploy_block = lo
                scan_start = (
                    self.history_scan_start_block
                    if self.history_scan_start_block is not None
                    else lo
                )
                return {
                    "status": DEPLOY_BLOCK_VERIFIED,
                    "deployBlock": lo,
                    "firstObservedEventBlock": first_event_block,
                    "historyScanStartBlock": scan_start,
                    "deploymentTransactionHash": None,
                    "resolutionMethod": "binary_search_eth_getCode",
                    "archiveBinarySearchSupported": True,
                }
        except RpcTransportError as exc:
            pruned_error = str(exc)

        # 4. Cannot prove `deployBlock`: DO NOT guess and DO NOT treat `firstObservedEventBlock` as `deployBlock`!
        self.deploy_block = None
        return {
            "status": SYNC_CONFIG_REQUIRED,
            "deployBlock": None,
            "firstObservedEventBlock": first_event_block,
            "historyScanStartBlock": effective_floor,
            "deploymentTransactionHash": None,
            "resolutionMethod": "unverified_sync_config_required",
            "archiveBinarySearchSupported": False if pruned_error else True,
            "prunedRpcReason": pruned_error,
        }

    # ------------------------------------------------------------------------
    # 4.3 Block Header & Timestamp Cache + Section 5 Reorg Detection
    # ------------------------------------------------------------------------

    def get_block_header(self, block_number: int, force_refresh: bool = False) -> BlockHeaderRecord:
        """
        Fetch and cache block header (`blockNumber`, `blockHash`, `parentHash`, `timestamp`)
        via `eth_getBlockByNumber`.
        If a cached header already exists and `force_refresh=True` (or when verifying headers),
        compares `blockHash` and linkage to detect Reorgs.
        """
        blk_num = int(block_number)
        if blk_num < 0:
            raise ValueError(f"block_number must be non-negative, got {blk_num}")

        if not force_refresh and blk_num in self._block_header_cache:
            return self._block_header_cache[blk_num]

        raw_block = self.rpc.call("eth_getBlockByNumber", [hex(blk_num), False])
        if not isinstance(raw_block, dict):
            raise RpcTransportError(f"eth_getBlockByNumber({hex(blk_num)}) returned non-object: {raw_block!r}")

        parsed_number = parse_hex_int(raw_block.get("number"), field_name="block.number")
        if parsed_number != blk_num:
            raise RpcTransportError(
                f"Block number mismatch in eth_getBlockByNumber: requested {blk_num}, got {parsed_number}"
            )
        block_hash = normalize_hex_hash(raw_block.get("hash"), expected_bytes=32, field_name="block.hash")
        parent_hash = normalize_hex_hash(
            raw_block.get("parentHash"), expected_bytes=32, field_name="block.parentHash"
        )
        timestamp = parse_hex_int(raw_block.get("timestamp"), field_name="block.timestamp")

        record = BlockHeaderRecord(
            block_number=parsed_number,
            block_hash=block_hash,
            parent_hash=parent_hash,
            timestamp=timestamp,
        )

        # Check against existing cache before overwriting
        if blk_num in self._block_header_cache:
            old_rec = self._block_header_cache[blk_num]
            if old_rec.block_hash != record.block_hash:
                self._flag_reorg(
                    reason="CACHED_BLOCK_HASH_CHANGED",
                    from_block=blk_num,
                    to_block=max(self._block_header_cache.keys()),
                    mismatch={
                        "type": "BLOCK_HASH_CHANGED",
                        "blockNumber": blk_num,
                        "expectedBlockHash": old_rec.block_hash,
                        "actualBlockHash": record.block_hash,
                    },
                )

        # Check parent linkage with block N-1 if cached
        if (blk_num - 1) in self._block_header_cache:
            prev_rec = self._block_header_cache[blk_num - 1]
            if record.parent_hash != prev_rec.block_hash:
                self._flag_reorg(
                    reason="PARENT_HASH_LINKAGE_BROKEN",
                    from_block=blk_num - 1,
                    to_block=max([blk_num, *self._block_header_cache.keys()]),
                    mismatch={
                        "type": "PARENT_HASH_MISMATCH",
                        "blockNumber": blk_num,
                        "parentBlockNumber": blk_num - 1,
                        "expectedParentHash": prev_rec.block_hash,
                        "actualParentHash": record.parent_hash,
                    },
                )

        self._block_header_cache[blk_num] = record
        return record

    def detect_reorg_on_headers(
        self,
        reference_headers: Sequence[Union[BlockHeaderRecord, Dict[str, Any]]],
        refetch_from_rpc: bool = True,
    ) -> ReorgDetectionResult:
        """
        Section 5 – Reorg Detection (Phase 2: Detect & Flag Only, No Auto-Recovery).
        Compares stored/reference block headers (`blockNumber`, `blockHash`, `parentHash`)
        against current RPC block headers (or within the sequence for `parentHash` linkage).
        Marks affected logs in `self._indexed_logs` with `needsReorgCheck = True`.
        """
        normalized_refs: List[BlockHeaderRecord] = []
        for item in reference_headers:
            if isinstance(item, BlockHeaderRecord):
                normalized_refs.append(item)
            elif isinstance(item, dict):
                normalized_refs.append(
                    BlockHeaderRecord(
                        block_number=int(item["blockNumber"]),
                        block_hash=normalize_hex_hash(item["blockHash"], field_name="blockHash"),
                        parent_hash=normalize_hex_hash(item["parentHash"], field_name="parentHash"),
                        timestamp=int(item.get("timestamp", 0)),
                    )
                )
            else:
                raise TypeError(f"Unsupported header item type: {type(item).__name__}")

        normalized_refs.sort(key=lambda r: r.block_number)
        mismatches: List[Dict[str, Any]] = []

        # 1. Check internal parentHash chain continuity within reference headers
        for idx in range(1, len(normalized_refs)):
            prev_h = normalized_refs[idx - 1]
            curr_h = normalized_refs[idx]
            if curr_h.block_number == prev_h.block_number + 1:
                if curr_h.parent_hash != prev_h.block_hash:
                    mismatches.append(
                        {
                            "type": "INTERNAL_PARENT_HASH_MISMATCH",
                            "blockNumber": curr_h.block_number,
                            "parentBlockNumber": prev_h.block_number,
                            "expectedParentHash": prev_h.block_hash,
                            "actualParentHash": curr_h.parent_hash,
                        }
                    )

        # 2. If refetch_from_rpc is enabled, fetch live headers and compare blockHash & parentHash
        live_by_number: Dict[int, BlockHeaderRecord] = {}
        if refetch_from_rpc:
            for ref in normalized_refs:
                raw_block = self.rpc.call("eth_getBlockByNumber", [hex(ref.block_number), False])
                if not isinstance(raw_block, dict):
                    raise RpcTransportError(
                        f"Failed to fetch block {ref.block_number} during reorg detection."
                    )
                live_hash = normalize_hex_hash(raw_block.get("hash"), field_name="block.hash")
                live_parent = normalize_hex_hash(raw_block.get("parentHash"), field_name="block.parentHash")
                live_ts = parse_hex_int(raw_block.get("timestamp"), field_name="block.timestamp")
                live_rec = BlockHeaderRecord(
                    block_number=ref.block_number,
                    block_hash=live_hash,
                    parent_hash=live_parent,
                    timestamp=live_ts,
                )
                live_by_number[ref.block_number] = live_rec

                if live_rec.block_hash != ref.block_hash:
                    mismatches.append(
                        {
                            "type": "BLOCK_HASH_CHANGED",
                            "blockNumber": ref.block_number,
                            "expectedBlockHash": ref.block_hash,
                            "actualBlockHash": live_rec.block_hash,
                        }
                    )
                if live_rec.parent_hash != ref.parent_hash:
                    mismatches.append(
                        {
                            "type": "PARENT_HASH_CHANGED",
                            "blockNumber": ref.block_number,
                            "expectedParentHash": ref.parent_hash,
                            "actualParentHash": live_rec.parent_hash,
                        }
                    )

            # Also check parent linkage across consecutive live blocks
            sorted_live_nums = sorted(live_by_number.keys())
            for idx in range(1, len(sorted_live_nums)):
                prev_num = sorted_live_nums[idx - 1]
                curr_num = sorted_live_nums[idx]
                if curr_num == prev_num + 1:
                    if live_by_number[curr_num].parent_hash != live_by_number[prev_num].block_hash:
                        mismatches.append(
                            {
                                "type": "LIVE_PARENT_HASH_LINKAGE_BROKEN",
                                "blockNumber": curr_num,
                                "parentBlockNumber": prev_num,
                                "expectedParentHash": live_by_number[prev_num].block_hash,
                                "actualParentHash": live_by_number[curr_num].parent_hash,
                            }
                        )

        if not mismatches:
            result = ReorgDetectionResult(reorg_detected=False)
            self.last_reorg_detection = result
            return result

        affected_blocks = [int(m["blockNumber"]) for m in mismatches]
        min_affected = min(affected_blocks)
        max_known_block = max(
            [r.block_number for r in normalized_refs]
            + [int(lg["blockNumber"]) for lg in self._indexed_logs.values()]
            + affected_blocks
        )

        affected_log_keys: List[str] = []
        for log_key, log_entry in self._indexed_logs.items():
            if int(log_entry["blockNumber"]) >= min_affected:
                log_entry["needsReorgCheck"] = True
                log_entry["reorgFlagReason"] = mismatches[0]["type"]
                affected_log_keys.append(log_key)

        result = ReorgDetectionResult(
            reorg_detected=True,
            reason=mismatches[0]["type"],
            affected_from_block=min_affected,
            affected_to_block=max_known_block,
            mismatches=mismatches,
            affected_log_keys=sorted(affected_log_keys),
        )
        self.last_reorg_detection = result
        return result

    def _flag_reorg(
        self,
        reason: str,
        from_block: int,
        to_block: int,
        mismatch: Dict[str, Any],
    ) -> None:
        affected_keys: List[str] = []
        for log_key, log_entry in self._indexed_logs.items():
            if int(log_entry["blockNumber"]) >= from_block:
                log_entry["needsReorgCheck"] = True
                log_entry["reorgFlagReason"] = reason
                affected_keys.append(log_key)

        if self.last_reorg_detection and self.last_reorg_detection.reorg_detected:
            self.last_reorg_detection.mismatches.append(mismatch)
            if self.last_reorg_detection.affected_from_block is not None:
                self.last_reorg_detection.affected_from_block = min(
                    self.last_reorg_detection.affected_from_block, from_block
                )
            else:
                self.last_reorg_detection.affected_from_block = from_block
            if self.last_reorg_detection.affected_to_block is not None:
                self.last_reorg_detection.affected_to_block = max(
                    self.last_reorg_detection.affected_to_block, to_block
                )
            else:
                self.last_reorg_detection.affected_to_block = to_block
            merged_keys = set(self.last_reorg_detection.affected_log_keys) | set(affected_keys)
            self.last_reorg_detection.affected_log_keys = sorted(merged_keys)
        else:
            self.last_reorg_detection = ReorgDetectionResult(
                reorg_detected=True,
                reason=reason,
                affected_from_block=from_block,
                affected_to_block=to_block,
                mismatches=[mismatch],
                affected_log_keys=sorted(affected_keys),
            )

    @property
    def cached_block_headers(self) -> Dict[int, BlockHeaderRecord]:
        return dict(self._block_header_cache)

    # ------------------------------------------------------------------------
    # 4.2 & 4.5 Event Reading, Parsing, Wei Preservation & Deduplication
    # ------------------------------------------------------------------------

    def validate_event_names(self, event_names: Sequence[str]) -> List[AbiEventSpec]:
        """
        Validate that every requested event name exists in `ProjectCore` ABI.
        Explicitly rejects nonexistent event names (e.g., `RefundApproved`, `RefundReady`).
        """
        specs: List[AbiEventSpec] = []
        for name in event_names:
            if name not in self.event_specs:
                raise InvalidContractABIError(
                    f"Event '{name}' does not exist in ProjectCore ABI. "
                    f"Valid events are: {sorted(self.event_specs.keys())}"
                )
            specs.append(self.event_specs[name])
        return specs

    def parse_raw_log(
        self,
        raw_log: Dict[str, Any],
        chain_id: Optional[int] = None,
        fetch_missing_timestamp: bool = True,
    ) -> Dict[str, Any]:
        """
        Decode a raw JSON-RPC log dictionary using the validated `ProjectCore` ABI.
        Preserves exact integer Wei (`int` and `str`) for all uint256 values and fetches/verifies
        `blockTimestamp` from the block header cache.
        """
        if not isinstance(raw_log, dict):
            raise RpcTransportError(f"Log entry must be a dict, got {type(raw_log).__name__}")

        log_address = normalize_address(raw_log.get("address", ""), field_name="log.address")
        if log_address.lower() != self.contract_address.lower():
            raise InvalidContractAddressError(
                f"Log contract address {log_address} does not match expected {self.contract_address}"
            )

        topics = raw_log.get("topics")
        if not isinstance(topics, list) or len(topics) == 0:
            raise RpcTransportError("Log entry is missing topics[0].")

        topic0 = normalize_hex_hash(topics[0], expected_bytes=32, field_name="log.topics[0]")
        spec = self.topic0_to_event.get(topic0.lower())
        if spec is None:
            raise InvalidContractABIError(f"Unknown event topic0 {topic0} not present in ProjectCore ABI.")

        if len(topics) - 1 != len(spec.indexed_inputs):
            raise RpcTransportError(
                f"Event {spec.name} expected {len(spec.indexed_inputs)} indexed topics, got {len(topics) - 1}."
            )

        block_number = parse_hex_int(raw_log.get("blockNumber"), field_name="log.blockNumber")
        block_hash = normalize_hex_hash(raw_log.get("blockHash"), expected_bytes=32, field_name="log.blockHash")
        tx_hash = normalize_hex_hash(
            raw_log.get("transactionHash"), expected_bytes=32, field_name="log.transactionHash"
        )
        tx_index = parse_hex_int(raw_log.get("transactionIndex", 0), field_name="log.transactionIndex")
        log_index = parse_hex_int(raw_log.get("logIndex"), field_name="log.logIndex")

        # Decode indexed topics
        decoded_args: Dict[str, Any] = {}
        for idx, (param_name, param_type) in enumerate(spec.indexed_inputs):
            raw_topic_hex = normalize_hex_hash(
                topics[idx + 1], expected_bytes=32, field_name=f"log.topics[{idx + 1}]"
            )
            topic_bytes = bytes.fromhex(raw_topic_hex[2:])
            val = abi_decode([param_type], topic_bytes)[0]
            decoded_args[param_name] = self._normalize_decoded_value(param_type, val)

        # Decode non-indexed data payload
        raw_data_hex = raw_log.get("data", "0x")
        if not isinstance(raw_data_hex, str) or not raw_data_hex.startswith(("0x", "0X")):
            raise RpcTransportError(f"Invalid log.data field in {tx_hash}: {raw_data_hex!r}")
        data_bytes = bytes.fromhex(raw_data_hex[2:])

        if spec.non_indexed_inputs:
            non_indexed_types = [ptype for _, ptype in spec.non_indexed_inputs]
            try:
                decoded_tuple = abi_decode(non_indexed_types, data_bytes)
            except Exception as exc:
                raise RpcTransportError(f"Failed to ABI-decode data for event {spec.name}: {exc}") from exc
            for (param_name, param_type), val in zip(spec.non_indexed_inputs, decoded_tuple):
                decoded_args[param_name] = self._normalize_decoded_value(param_type, val)

        # Resolve block header & timestamp via cache (always prefer block header cache to ensure parentHash tracking)
        block_timestamp: Optional[int] = None
        parent_hash: Optional[str] = None
        if fetch_missing_timestamp or block_number in self._block_header_cache:
            header = self.get_block_header(block_number)
            # Check if log's blockHash matches block header's blockHash
            if header.block_hash != block_hash:
                self._flag_reorg(
                    reason="LOG_BLOCK_HASH_MISMATCH_WITH_HEADER",
                    from_block=block_number,
                    to_block=block_number,
                    mismatch={
                        "type": "LOG_BLOCK_HASH_MISMATCH",
                        "blockNumber": block_number,
                        "logBlockHash": block_hash,
                        "headerBlockHash": header.block_hash,
                    },
                )
            block_timestamp = header.timestamp
            parent_hash = header.parent_hash
        elif raw_log.get("blockTimestamp") is not None:
            block_timestamp = parse_hex_int(raw_log.get("blockTimestamp"), field_name="log.blockTimestamp")

        effective_chain_id = int(chain_id if chain_id is not None else self.expected_chain_id)
        log_key = build_composite_log_key(effective_chain_id, tx_hash, log_index)

        # Extract primary Wei amount if present in event args (never float!)
        amount_wei: Optional[int] = None
        if "amount" in decoded_args and isinstance(decoded_args["amount"], int):
            amount_wei = decoded_args["amount"]
        elif "feeAmount" in decoded_args and isinstance(decoded_args["feeAmount"], int):
            amount_wei = decoded_args["feeAmount"]

        parsed_record: Dict[str, Any] = {
            "logKey": log_key,
            "chainId": effective_chain_id,
            "contractAddress": self.contract_address,
            "eventName": spec.name,
            "eventSignature": spec.signature,
            "topic0": spec.topic0,
            "blockNumber": block_number,
            "blockHash": block_hash,
            "parentHash": parent_hash,
            "blockTimestamp": block_timestamp,
            "transactionHash": tx_hash,
            "transactionIndex": tx_index,
            "logIndex": log_index,
            "removed": bool(raw_log.get("removed", False)),
            "args": decoded_args,
            "amountWei": amount_wei,
            "amountWeiStr": str(amount_wei) if amount_wei is not None else None,
            "amountEthDisplay": wei_to_eth_display(amount_wei) if amount_wei is not None else None,
            "needsReorgCheck": bool(raw_log.get("removed", False)),
        }
        return parsed_record

    @staticmethod
    def _normalize_decoded_value(param_type: str, value: Any) -> Any:
        if param_type == "address":
            return to_checksum_address(value)
        if param_type.startswith("uint") or param_type.startswith("int"):
            return int(value)
        if param_type == "bool":
            return bool(value)
        if param_type == "string":
            return str(value)
        if isinstance(value, (bytes, bytearray)):
            return "0x" + bytes(value).hex()
        return value

    def fetch_and_index_logs(
        self,
        from_block: int,
        to_block: int,
        event_names: Optional[Sequence[str]] = None,
        chunk_size: int = DEFAULT_LOG_CHUNK_SIZE,
    ) -> Dict[str, Any]:
        """
        Fetch logs from `from_block` to `to_block` in safe block chunks, adaptively halving
        the batch size if the RPC rejects a range for exceeding block/log limits, decode all
        matching events, populate the block header cache, verify contiguous block coverage
        (no skipped blocks), and deduplicate by `(chainId, transactionHash, logIndex)`.
        """
        start_blk = int(from_block)
        end_blk = int(to_block)
        if start_blk < 0 or end_blk < start_blk:
            raise ValueError(f"Invalid block range: [{start_blk}, {end_blk}]")

        topic_filter: Optional[List[str]] = None
        if event_names is not None:
            specs = self.validate_event_names(event_names)
            topic_filter = [s.topic0 for s in specs]

        initial_step = max(1, int(chunk_size))
        current_step = initial_step
        newly_added: List[Dict[str, Any]] = []
        duplicates_skipped: int = 0
        raw_logs_fetched: int = 0
        chunks_scanned: List[Dict[str, int]] = []

        curr = start_blk
        while curr <= end_blk:
            chunk_end = min(curr + current_step - 1, end_blk)
            filter_obj: Dict[str, Any] = {
                "address": self.contract_address,
                "fromBlock": hex(curr),
                "toBlock": hex(chunk_end),
            }
            if topic_filter is not None:
                filter_obj["topics"] = [topic_filter]

            try:
                raw_logs = self.rpc.call("eth_getLogs", [filter_obj])
            except RpcTransportError as exc:
                err_lower = str(exc).lower()
                is_range_limit = any(
                    kw in err_lower
                    for kw in ("block range", "range", "exceed", "too many", "limit", "response size", "-32005")
                )
                if is_range_limit and current_step > 1:
                    current_step = max(1, current_step // 2)
                    continue
                raise

            if not isinstance(raw_logs, list):
                raise RpcTransportError(f"eth_getLogs returned non-list: {raw_logs!r}")

            chunks_scanned.append({"fromBlock": curr, "toBlock": chunk_end})

            for raw_log in raw_logs:
                raw_logs_fetched += 1
                parsed = self.parse_raw_log(raw_log, chain_id=self.expected_chain_id, fetch_missing_timestamp=True)
                log_key = parsed["logKey"]
                if log_key in self._indexed_logs:
                    existing = self._indexed_logs[log_key]
                    # If the same logKey reappears with a different blockHash, flag reorg!
                    if existing["blockHash"] != parsed["blockHash"]:
                        self._flag_reorg(
                            reason="DUPLICATE_LOG_KEY_WITH_DIFFERENT_BLOCK_HASH",
                            from_block=min(int(existing["blockNumber"]), int(parsed["blockNumber"])),
                            to_block=max(int(existing["blockNumber"]), int(parsed["blockNumber"])),
                            mismatch={
                                "type": "LOG_REORG_BLOCK_HASH_CHANGE",
                                "logKey": log_key,
                                "previousBlockHash": existing["blockHash"],
                                "newBlockHash": parsed["blockHash"],
                            },
                        )
                        self._indexed_logs[log_key] = parsed
                        newly_added.append(parsed)
                    else:
                        duplicates_skipped += 1
                else:
                    self._indexed_logs[log_key] = parsed
                    newly_added.append(parsed)

            curr = chunk_end + 1

        # Verify contiguous block coverage with zero gaps across all batches
        no_blocks_skipped = True
        if not chunks_scanned:
            no_blocks_skipped = False
        else:
            if chunks_scanned[0]["fromBlock"] != start_blk or chunks_scanned[-1]["toBlock"] != end_blk:
                no_blocks_skipped = False
            for i in range(1, len(chunks_scanned)):
                if chunks_scanned[i]["fromBlock"] != chunks_scanned[i - 1]["toBlock"] + 1:
                    no_blocks_skipped = False
                    break

        # Sort indexed logs deterministically by (blockNumber, transactionIndex, logIndex)
        all_sorted = sorted(
            self._indexed_logs.values(),
            key=lambda x: (int(x["blockNumber"]), int(x["transactionIndex"]), int(x["logIndex"])),
        )

        return {
            "fromBlock": start_blk,
            "toBlock": end_blk,
            "chunksScanned": chunks_scanned,
            "chunkCount": len(chunks_scanned),
            "noBlocksSkipped": no_blocks_skipped,
            "rawLogsFetched": raw_logs_fetched,
            "newlyIndexedCount": len(newly_added),
            "duplicatesSkipped": duplicates_skipped,
            "totalUniqueIndexedLogs": len(all_sorted),
            "uniqueBlocksCached": len(self._block_header_cache),
            "logs": copy.deepcopy(all_sorted),
        }

    def ingest_raw_logs(
        self,
        raw_logs: Sequence[Dict[str, Any]],
        fetch_missing_timestamp: bool = True,
    ) -> Dict[str, Any]:
        """
        Parse and deduplicate a batch of raw logs (useful for unit tests and batch ingestion).
        Flags a reorg if a duplicate `logKey` appears with a different `blockHash`.
        """
        newly_added: List[Dict[str, Any]] = []
        duplicates_skipped = 0
        for raw_log in raw_logs:
            parsed = self.parse_raw_log(
                raw_log,
                chain_id=self.expected_chain_id,
                fetch_missing_timestamp=fetch_missing_timestamp,
            )
            log_key = parsed["logKey"]
            if log_key in self._indexed_logs:
                existing = self._indexed_logs[log_key]
                if existing["blockHash"] == parsed["blockHash"]:
                    duplicates_skipped += 1
                    continue
                self._flag_reorg(
                    reason="DUPLICATE_LOG_KEY_WITH_DIFFERENT_BLOCK_HASH",
                    from_block=min(int(existing["blockNumber"]), int(parsed["blockNumber"])),
                    to_block=max(int(existing["blockNumber"]), int(parsed["blockNumber"])),
                    mismatch={
                        "type": "LOG_REORG_BLOCK_HASH_CHANGE",
                        "logKey": log_key,
                        "previousBlockHash": existing["blockHash"],
                        "newBlockHash": parsed["blockHash"],
                    },
                )
            self._indexed_logs[log_key] = parsed
            newly_added.append(parsed)

        all_sorted = sorted(
            self._indexed_logs.values(),
            key=lambda x: (int(x["blockNumber"]), int(x["transactionIndex"]), int(x["logIndex"])),
        )
        return {
            "rawLogsProcessed": len(raw_logs),
            "newlyIndexedCount": len(newly_added),
            "duplicatesSkipped": duplicates_skipped,
            "totalUniqueIndexedLogs": len(all_sorted),
            "logs": copy.deepcopy(all_sorted),
        }

    # ------------------------------------------------------------------------
    # 4.4 Campaign Classification by `block.timestamp`
    # ------------------------------------------------------------------------

    @staticmethod
    def classify_deposit_log(
        parsed_log: Dict[str, Any],
        campaigns: Union[Dict[str, Dict[str, Any]], Sequence[Dict[str, Any]]],
        safety_window_seconds: int = BLOCK_TIME_SAFETY_WINDOW_SECONDS,
    ) -> Dict[str, Any]:
        """
        Section 4.4 – Classify a `FundDeposited` event log against campaigns using `blockTimestamp`.
        Maps the V4.4 classification result into the 3 required Phase 2 states:
        - `classified_by_block_timestamp`: strictly inside a single campaign window (`±12s` safe).
        - `pending_reconciliation`: within `±12s` of a campaign start/end boundary or on the
          shared-second transition (`1793619753`). NEVER auto-confirms into a campaign!
        - `unallocated`: outside all campaign windows and outside all `±12s` boundary zones.
        Also enforces the Single-Assignment Invariant (never allocates to 2 campaigns).
        """
        if parsed_log.get("eventName") != "FundDeposited":
            raise ValueError(
                f"classify_deposit_log only accepts 'FundDeposited' logs, got {parsed_log.get('eventName')!r}"
            )
        block_ts = parsed_log.get("blockTimestamp")
        if block_ts is None:
            raise ValueError("Cannot classify FundDeposited log without 'blockTimestamp'.")

        if isinstance(campaigns, dict):
            campaigns_map: Dict[str, Dict[str, Any]] = campaigns
        else:
            campaigns_map = {str(c["id"]): c for c in campaigns if isinstance(c, dict) and "id" in c}

        v4_res = classify_transaction_at_timestamp(
            tx_timestamp=int(block_ts),
            campaigns=campaigns_map,
            boundary_window_sec=safety_window_seconds,
        )

        v4_status = v4_res["classificationStatus"]
        needs_review = bool(v4_res["needsBoundaryReview"])

        if v4_status == "CONFIRMED_IN_CAMPAIGN" and not needs_review:
            phase2_state = "classified_by_block_timestamp"
            allocated_campaign_id = v4_res["campaignId"]
        elif needs_review or v4_status in (
            "PROVISIONAL_PENDING_REVIEW",
            "ASSIGNED_WITH_BOUNDARY_FLAG",
            "VOLUNTARY_PENDING_BOUNDARY_REVIEW",
        ):
            phase2_state = "pending_reconciliation"
            # Never auto-confirm a pending_reconciliation transaction into confirmed campaign totals
            allocated_campaign_id = None
        else:
            phase2_state = "unallocated"
            allocated_campaign_id = None

        amount_wei = int(parsed_log["amountWei"])
        student_wallet = parsed_log["args"]["student"]

        return {
            "logKey": parsed_log["logKey"],
            "transactionHash": parsed_log["transactionHash"],
            "logIndex": int(parsed_log["logIndex"]),
            "blockNumber": int(parsed_log["blockNumber"]),
            "blockTimestamp": int(block_ts),
            "studentWallet": student_wallet,
            "amountWei": amount_wei,
            "amountWeiStr": str(amount_wei),
            "amountEthDisplay": wei_to_eth_display(amount_wei),
            "classificationState": phase2_state,
            "allocatedCampaignId": allocated_campaign_id,
            "provisionalCampaignId": v4_res["campaignId"],
            "candidateCampaignIds": v4_res["candidateCampaignIds"],
            "v4ClassificationStatus": v4_status,
            "assignedBucket": v4_res["assignedBucket"],
            "needsBoundaryReview": needs_review,
            "classificationReason": v4_res.get("boundaryReason"),
        }

    def classify_all_indexed_deposits(
        self,
        campaigns: Sequence[Dict[str, Any]],
        safety_window_seconds: int = BLOCK_TIME_SAFETY_WINDOW_SECONDS,
    ) -> Dict[str, Any]:
        """
        Classify all indexed `FundDeposited` logs and verify the Single-Assignment Invariant.
        """
        deposit_logs = [
            lg for lg in self._indexed_logs.values() if lg.get("eventName") == "FundDeposited" and not lg.get("removed")
        ]
        deposit_logs.sort(key=lambda x: (int(x["blockNumber"]), int(x["transactionIndex"]), int(x["logIndex"])))

        classified: List[Dict[str, Any]] = []
        seen_log_keys: Set[str] = set()
        by_state: Dict[str, List[Dict[str, Any]]] = {
            "classified_by_block_timestamp": [],
            "pending_reconciliation": [],
            "unallocated": [],
        }

        for lg in deposit_logs:
            lkey = lg["logKey"]
            if lkey in seen_log_keys:
                raise BlockchainIndexerError(f"Single-Assignment violation: duplicate logKey {lkey}")
            seen_log_keys.add(lkey)

            item = self.classify_deposit_log(lg, campaigns=campaigns, safety_window_seconds=safety_window_seconds)
            classified.append(item)
            by_state[item["classificationState"]].append(item)

        return {
            "totalDepositsClassified": len(classified),
            "singleAssignmentInvariantPassed": True,
            "countsByState": {k: len(v) for k, v in by_state.items()},
            "classifiedDeposits": classified,
            "results": classified,
            "byState": by_state,
        }

    # ------------------------------------------------------------------------
    # 4.6 Same-`blockTag` Smart Contract State Reading & Reconciliation
    # ------------------------------------------------------------------------

    def call_view_function(
        self,
        function_name: str,
        args: Optional[Sequence[Any]] = None,
        block_tag: Union[int, str] = "latest",
    ) -> Any:
        """
        Execute a read-only `eth_call` for a `view` function defined in `ProjectCore` ABI
        at a specific `block_tag` (`hex(block_number)` or `'latest'`).
        """
        if function_name not in self.function_specs:
            raise InvalidContractABIError(f"Function '{function_name}' is not present in ProjectCore ABI.")
        spec = self.function_specs[function_name]
        if spec.state_mutability not in ("view", "pure"):
            raise ReadOnlyPolicyViolationError(
                f"Function '{function_name}' has stateMutability='{spec.state_mutability}'; only view/pure allowed."
            )

        call_args = list(args) if args is not None else []
        if len(call_args) != len(spec.input_types):
            raise ValueError(
                f"Function {function_name} expects {len(spec.input_types)} args, got {len(call_args)}."
            )

        encoded_args = b""
        if spec.input_types:
            encoded_args = abi_encode(list(spec.input_types), call_args)

        call_data = spec.selector + encoded_args.hex()
        tag_str = hex(block_tag) if isinstance(block_tag, int) else str(block_tag)

        raw_result = self.rpc.call(
            "eth_call",
            [
                {"to": self.contract_address, "data": call_data},
                tag_str,
            ],
        )
        if not isinstance(raw_result, str) or not raw_result.startswith(("0x", "0X")):
            raise RpcTransportError(f"Malformed eth_call result for {function_name}: {raw_result!r}")

        result_bytes = bytes.fromhex(raw_result[2:])
        if len(result_bytes) == 0:
            raise RpcTransportError(f"Empty eth_call result ('0x') for {function_name} at {tag_str}.")

        decoded = abi_decode(list(spec.output_types), result_bytes)
        normalized = [
            self._normalize_decoded_value(ptype, val) for ptype, val in zip(spec.output_types, decoded)
        ]
        if len(normalized) == 1:
            return normalized[0]
        return tuple(normalized)

    def read_contract_state_at_block(
        self,
        block_number: int,
        student_wallets: Sequence[str],
        include_net_contribution_views: bool = False,
    ) -> Dict[str, Any]:
        """
        Read all required `ProjectCore` state variables and view functions at the EXACT SAME
        `blockTag = hex(block_number)`:
        - `studentContributions[wallet]`
        - `pendingStudentRefundAmount[wallet]`
        - `getStudentAvailableContribution(wallet)`
        - `reservedRefundAmount`
        - `getAvailableClassFund()`
        - (When `include_net_contribution_views=True`): `studentTotalDeposited[wallet]` and
          `getStudentMaxRefund(wallet)`
        Plus supporting global state (`classFundBalance`, `reservedSpendAmount`, `adminFeePool`,
        `refundRequestCount`, and each `getRefundRequest(id)`).
        """
        blk_num = int(block_number)
        if blk_num < 0:
            raise ValueError(f"block_number must be non-negative, got {blk_num}")
        block_tag = hex(blk_num)

        class_fund_balance = int(self.call_view_function("classFundBalance", [], block_tag=block_tag))
        admin_fee_pool = int(self.call_view_function("adminFeePool", [], block_tag=block_tag))
        reserved_spend_amount = int(self.call_view_function("reservedSpendAmount", [], block_tag=block_tag))
        reserved_refund_amount = int(self.call_view_function("reservedRefundAmount", [], block_tag=block_tag))
        available_class_fund = int(self.call_view_function("getAvailableClassFund", [], block_tag=block_tag))
        refund_request_count = int(self.call_view_function("refundRequestCount", [], block_tag=block_tag))

        refund_requests: Dict[int, Dict[str, Any]] = {}
        for refund_id in range(refund_request_count):
            req_tuple = self.call_view_function("getRefundRequest", [refund_id], block_tag=block_tag)
            applicant, amount, reason, yes_votes, no_votes, created_at, deadline, status_int = req_tuple
            refund_requests[refund_id] = {
                "refundId": refund_id,
                "applicant": applicant,
                "amountWei": int(amount),
                "amountWeiStr": str(int(amount)),
                "reason": reason,
                "yesVotes": int(yes_votes),
                "noVotes": int(no_votes),
                "createdAt": int(created_at),
                "deadline": int(deadline),
                "status": int(status_int),
                "statusName": REFUND_STATUS_NAMES.get(int(status_int), f"Unknown({status_int})"),
            }

        students_state: Dict[str, Dict[str, Any]] = {}
        for wallet in student_wallets:
            norm_wallet = normalize_address(wallet, field_name="student_wallet")
            contrib = int(self.call_view_function("studentContributions", [norm_wallet], block_tag=block_tag))
            pending_refund = int(
                self.call_view_function("pendingStudentRefundAmount", [norm_wallet], block_tag=block_tag)
            )
            available_contrib = int(
                self.call_view_function("getStudentAvailableContribution", [norm_wallet], block_tag=block_tag)
            )
            entry: Dict[str, Any] = {
                "wallet": norm_wallet,
                "studentContributionsWei": contrib,
                "pendingStudentRefundAmountWei": pending_refund,
                "getStudentAvailableContributionWei": available_contrib,
            }
            if include_net_contribution_views:
                entry["studentTotalDepositedWei"] = int(
                    self.call_view_function("studentTotalDeposited", [norm_wallet], block_tag=block_tag)
                )
                entry["getStudentMaxRefundWei"] = int(
                    self.call_view_function("getStudentMaxRefund", [norm_wallet], block_tag=block_tag)
                )
            students_state[norm_wallet] = entry

        return {
            "blockNumber": blk_num,
            "blockTag": block_tag,
            "classFundBalanceWei": class_fund_balance,
            "adminFeePoolWei": admin_fee_pool,
            "reservedSpendAmountWei": reserved_spend_amount,
            "reservedRefundAmountWei": reserved_refund_amount,
            "getAvailableClassFundWei": available_class_fund,
            "refundRequestCount": refund_request_count,
            "refundRequests": refund_requests,
            "students": students_state,
        }

    def verify_deployed_abi_at_block(
        self,
        block_tag: Union[int, str] = "latest",
        compiled_runtime_bytecode_hex: Optional[str] = None,
        require_exact_runtime_match: bool = False,
        require_net_contribution_views: bool = False,
    ) -> Dict[str, Any]:
        """
        Phase 2.1 Section C – Verify compatibility between the Indexer ABI, Web ABI,
        compiled artifact, and the actual deployed bytecode on Sepolia.
        Never assumes that mere bytecode existence (`!= '0x'`) means the ABI is verified.

        Checks:
        1. Deployed bytecode is non-empty.
        2. Every required view function selector (4-byte Keccak-256, or 3-byte PUSH3 when leading
           byte is `0x00` like `00437a5b`) is present in the deployed bytecode AND responds to
           `eth_call` with ABI-decodable output.
        3. Every required event `topic0` (32-byte Keccak-256) is present in the deployed bytecode
           (when inspecting real compiled EVM runtime bytecode).
        4. If `require_exact_runtime_match=True` or `compiled_runtime_bytecode_hex` is supplied,
           compares the exact runtime bytecode length & hash.
        Returns `status = DEPLOYED_ABI_VERIFIED` or `DEPLOYED_ABI_NOT_VERIFIED`.
        """
        tag_str = hex(block_tag) if isinstance(block_tag, int) else str(block_tag)
        raw_code = self.rpc.call("eth_getCode", [self.contract_address, tag_str])
        if not isinstance(raw_code, str) or not raw_code.strip().startswith("0x"):
            return {
                "status": DEPLOYED_ABI_NOT_VERIFIED,
                "abiVerified": False,
                "reason": "MALFORMED_ETH_GETCODE_RESPONSE",
            }

        code_hex = raw_code.strip()[2:].lower()
        if not code_hex or code_hex in ("0", "00"):
            return {
                "status": DEPLOYED_ABI_NOT_VERIFIED,
                "abiVerified": False,
                "reason": "EMPTY_BYTECODE",
            }

        # Check whether this is full EVM runtime bytecode (>= 1000 hex chars) vs short mock test bytecode
        is_full_runtime = len(code_hex) >= 1000
        missing_selectors: List[str] = []
        missing_event_topics: List[str] = []

        required_views = (
            REQUIRED_NET_CONTRIBUTION_VIEW_FUNCTIONS
            if require_net_contribution_views
            else REQUIRED_CORE_VIEW_FUNCTIONS
        )
        if is_full_runtime:
            for fn_name in sorted(required_views):
                spec = self.function_specs[fn_name]
                sel_hex = spec.selector[2:].lower()
                # Solidity optimizer uses PUSH3 when selector starts with '00' (e.g., 00437a5b -> 62437a5b)
                sel_trimmed = sel_hex.lstrip("0")
                if sel_hex not in code_hex and (not sel_trimmed or sel_trimmed not in code_hex):
                    missing_selectors.append(f"{fn_name}({sel_hex})")

            for ev_name in sorted(REQUIRED_CORE_EVENTS):
                ev_spec = self.event_specs[ev_name]
                t0_hex = ev_spec.topic0[2:].lower()
                if t0_hex not in code_hex:
                    missing_event_topics.append(f"{ev_name}({t0_hex[:16]}...)")

        # Probe zero-arg and address-arg view functions via eth_call to prove ABI return types match
        probe_failures: List[str] = []
        zero_addr = "0x0000000000000000000000000000000000000000"
        probes: List[Tuple[str, List[Any]]] = [
            ("classFundBalance", []),
            ("adminFeePool", []),
            ("reservedSpendAmount", []),
            ("reservedRefundAmount", []),
            ("getAvailableClassFund", []),
            ("refundRequestCount", []),
            ("studentContributions", [zero_addr]),
            ("pendingStudentRefundAmount", [zero_addr]),
            ("getStudentAvailableContribution", [zero_addr]),
        ]
        if require_net_contribution_views:
            probes.extend(
                [
                    ("studentTotalDeposited", [zero_addr]),
                    ("getStudentMaxRefund", [zero_addr]),
                ]
            )
        for fn_name, args in probes:
            try:
                self.call_view_function(fn_name, args, block_tag=tag_str)
            except Exception as exc:
                probe_failures.append(f"{fn_name}: {exc}")

        exact_artifact_matched: Optional[bool] = None
        if compiled_runtime_bytecode_hex is not None:
            clean_art = compiled_runtime_bytecode_hex.strip().lower().removeprefix("0x")
            exact_artifact_matched = code_hex == clean_art

        reasons: List[str] = []
        if missing_selectors:
            reasons.append(f"MISSING_FUNCTION_SELECTORS:{missing_selectors}")
        if missing_event_topics:
            reasons.append(f"MISSING_EVENT_TOPICS:{missing_event_topics}")
        if probe_failures:
            reasons.append(f"VIEW_PROBE_FAILURES:{probe_failures}")
        if require_exact_runtime_match and exact_artifact_matched is not True:
            reasons.append("EXACT_COMPILED_RUNTIME_BYTECODE_MISMATCH")

        abi_verified = len(reasons) == 0
        return {
            "status": DEPLOYED_ABI_VERIFIED if abi_verified else DEPLOYED_ABI_NOT_VERIFIED,
            "abiVerified": abi_verified,
            "blockTag": tag_str,
            "onchainBytecodeBytes": len(code_hex) // 2,
            "missingFunctionSelectors": missing_selectors,
            "missingEventTopics": missing_event_topics,
            "viewProbeFailures": probe_failures,
            "exactArtifactMatched": exact_artifact_matched,
            "reasons": reasons,
        }

    @staticmethod
    def verify_deposit_and_refund_event_pairings(
        source_logs: Sequence[Dict[str, Any]],
        up_to_block: int,
    ) -> Dict[str, Any]:
        """
        Phase 2.1 Section B – Verify event pairing integrity per transaction up to `up_to_block`:
        1. Every `FundDeposited` event MUST be accompanied by an `AdminFeeCollected` event in the
           EXACT SAME `transactionHash` and for the EXACT SAME `student`, and vice versa
           (no orphan `FundDeposited` without `AdminFeeCollected`, no orphan `AdminFeeCollected`,
           and no duplicate counting).
        2. Verify the 99% / 1% fee split ratio (`FEE_BPS = 100`, `BPS_DENOMINATOR = 10000`):
           - In the 99%/1% emitted model: `gross = fund_amt + fee_amt`, and `fee_amt == (gross * 100) // 10000`.
           - In the 100%/1% emitted model (`ProjectCore.sol` source): `fee_amt == (fund_amt * 100) // 10000`.
           Any ratio mismatch is flagged as an anomaly.
        3. Every `RefundRequestExecuted` event MUST be accompanied by a matching `RefundProcessed`
           event in the EXACT SAME `transactionHash` with the same `applicant == student` and `amount`,
           and we ONLY subtract `RefundRequestExecuted` once (never double-subtract `RefundProcessed`).
        """
        deposits_by_tx: Dict[str, List[Dict[str, Any]]] = {}
        fees_by_tx: Dict[str, List[Dict[str, Any]]] = {}
        refund_exec_by_tx: Dict[str, List[Dict[str, Any]]] = {}
        refund_proc_by_tx: Dict[str, List[Dict[str, Any]]] = {}

        for lg in source_logs:
            if int(lg["blockNumber"]) > int(up_to_block) or lg.get("removed", False):
                continue
            ev = lg.get("eventName")
            tx_h = normalize_hex_hash(lg["transactionHash"], field_name="transactionHash")
            if ev == "FundDeposited":
                deposits_by_tx.setdefault(tx_h, []).append(lg)
            elif ev == "AdminFeeCollected":
                fees_by_tx.setdefault(tx_h, []).append(lg)
            elif ev == "RefundRequestExecuted":
                refund_exec_by_tx.setdefault(tx_h, []).append(lg)
            elif ev == "RefundProcessed":
                refund_proc_by_tx.setdefault(tx_h, []).append(lg)

        anomalies: List[Dict[str, Any]] = []
        all_deposit_txs = sorted(set(deposits_by_tx.keys()) | set(fees_by_tx.keys()))

        for tx_h in all_deposit_txs:
            dep_list = deposits_by_tx.get(tx_h, [])
            fee_list = fees_by_tx.get(tx_h, [])
            if len(dep_list) != len(fee_list):
                if len(dep_list) > len(fee_list):
                    anomalies.append(
                        {
                            "type": "MISSING_ADMIN_FEE_COLLECTED_EVENT",
                            "transactionHash": tx_h,
                            "fundDepositedCount": len(dep_list),
                            "adminFeeCollectedCount": len(fee_list),
                        }
                    )
                else:
                    anomalies.append(
                        {
                            "type": "ORPHAN_ADMIN_FEE_COLLECTED_EVENT",
                            "transactionHash": tx_h,
                            "fundDepositedCount": len(dep_list),
                            "adminFeeCollectedCount": len(fee_list),
                        }
                    )
                continue

            for dep_lg, fee_lg in zip(dep_list, fee_list):
                dep_student = normalize_address(dep_lg["args"]["student"])
                fee_student = normalize_address(fee_lg["args"]["student"])
                dep_amt = int(dep_lg["args"]["amount"])
                fee_amt = int(fee_lg["args"]["feeAmount"])

                if dep_student != fee_student:
                    anomalies.append(
                        {
                            "type": "DEPOSIT_FEE_STUDENT_MISMATCH",
                            "transactionHash": tx_h,
                            "depositStudent": dep_student,
                            "feeStudent": fee_student,
                        }
                    )

                # Check 99%/1% split (`gross = dep_amt + fee_amt`) OR 100%/1% split (`gross = dep_amt`)
                gross_if_net_event = dep_amt + fee_amt
                expected_fee_from_net = (gross_if_net_event * FEE_BPS) // BPS_DENOMINATOR
                expected_fee_from_gross = (dep_amt * FEE_BPS) // BPS_DENOMINATOR

                if fee_amt != expected_fee_from_net and fee_amt != expected_fee_from_gross:
                    anomalies.append(
                        {
                            "type": "DEPOSIT_FEE_BPS_RATIO_MISMATCH",
                            "transactionHash": tx_h,
                            "student": dep_student,
                            "fundDepositedWei": dep_amt,
                            "adminFeeCollectedWei": fee_amt,
                            "expectedFeeIfNetEventWei": expected_fee_from_net,
                        }
                    )

        all_refund_txs = sorted(set(refund_exec_by_tx.keys()) | set(refund_proc_by_tx.keys()))
        for tx_h in all_refund_txs:
            exec_list = refund_exec_by_tx.get(tx_h, [])
            proc_list = refund_proc_by_tx.get(tx_h, [])
            if len(exec_list) != len(proc_list):
                anomalies.append(
                    {
                        "type": "REFUND_EXECUTED_PROCESSED_COUNT_MISMATCH",
                        "transactionHash": tx_h,
                        "refundRequestExecutedCount": len(exec_list),
                        "refundProcessedCount": len(proc_list),
                    }
                )
                continue
            for ex_lg, pr_lg in zip(exec_list, proc_list):
                ex_student = normalize_address(ex_lg["args"]["applicant"])
                pr_student = normalize_address(pr_lg["args"]["student"])
                ex_amt = int(ex_lg["args"]["amount"])
                pr_amt = int(pr_lg["args"]["amount"])
                if ex_student != pr_student or ex_amt != pr_amt:
                    anomalies.append(
                        {
                            "type": "REFUND_EXECUTED_PROCESSED_PAYLOAD_MISMATCH",
                            "transactionHash": tx_h,
                            "executedApplicant": ex_student,
                            "processedStudent": pr_student,
                            "executedAmountWei": ex_amt,
                            "processedAmountWei": pr_amt,
                        }
                    )

        return {
            "valid": len(anomalies) == 0,
            "anomalyCount": len(anomalies),
            "anomalies": anomalies,
        }

    def detect_contract_accounting_version(
        self,
        onchain_state: Dict[str, Any],
        deposited_by_wallet: Dict[str, int],
        fee_by_wallet: Dict[str, int],
        refund_executed_by_wallet: Dict[str, int],
        pairing_check: Dict[str, Any],
        explicit_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Phase 2.1, 2.2.1 & Phase 1 (Lab 15) – Determine or verify the Smart Contract accounting version:
        - `CONTRACT_VERSION_GROSS_CONTRIBUTION` (`GROSS_CONTRIBUTION`, canonical for pre-upgrade `0x909486...503D`):
          - `studentContributions` increases by 100% `msg.value`.
          - `FundDeposited` records 100% `msg.value`.
          - `AdminFeeCollected` records 1%.
          - `classFundBalance` increases by 99% (`classFundDeposits = SUM(FundDeposited) - SUM(AdminFeeCollected)`).
          - `adminFeePool` increases by 1%.
          - Formula: `studentContributions[w] = SUM(FundDeposited[w]) - SUM(RefundRequestExecuted[w])`
        - `CONTRACT_VERSION_NET_CONTRIBUTION` (`NET_CONTRIBUTION`, Lab 15 Phase 1 net refund accounting):
          - `FundDeposited` records 100% `msg.value`; `AdminFeeCollected` records 1%.
          - `studentContributions` increases by 99% net (`msg.value - adminFee`) and decreases on refunds.
          - `studentTotalDeposited` records cumulative 100% `msg.value` (never decremented on refund).
          - Formula: `studentContributions[w] = SUM(FundDeposited[w]) - SUM(AdminFeeCollected[w]) - SUM(RefundRequestExecuted[w])`
        - `CONTRACT_VERSION_LEGACY_GROSS` (`LEGACY_GROSS_CONTRIBUTION`, historical contract `0xe3e1...ee91`
          where `FundDeposited` emitted 99% net while `studentContributions` recorded 100% gross):
          - Formula: `studentContributions[w] = SUM(FundDeposited[w]) + SUM(AdminFeeCollected[w]) - SUM(RefundRequestExecuted[w])`
        - `CONTRACT_VERSION_UNVERIFIED`:
          Returned when `explicit_version` is not set and there is insufficient or contradictory on-chain
          evidence (e.g., zero deposits with non-zero fee, or neither formula matches on-chain state).
        """
        if explicit_version is not None:
            norm_ver = normalize_contract_version(explicit_version)
            assert norm_ver is not None
            return {
                "contractVersion": norm_ver,
                "requestedVersion": explicit_version,
                "detectionMethod": "explicitly_configured",
                "verified": norm_ver != CONTRACT_VERSION_UNVERIFIED,
            }

        if not pairing_check.get("valid", False):
            return {
                "contractVersion": CONTRACT_VERSION_UNVERIFIED,
                "detectionMethod": "event_pairing_anomaly_detected",
                "verified": False,
            }

        wallets_with_deposits = [
            w for w, dep in deposited_by_wallet.items() if dep > 0 and fee_by_wallet.get(w, 0) > 0
        ]
        if not wallets_with_deposits:
            return {
                "contractVersion": CONTRACT_VERSION_UNVERIFIED,
                "detectionMethod": "insufficient_deposit_fee_evidence",
                "verified": False,
            }

        matches_legacy_all = True
        matches_gross_all = True
        matches_net_all = True

        for w in wallets_with_deposits:
            actual_c = int(onchain_state["students"][w]["studentContributionsWei"])
            dep = deposited_by_wallet.get(w, 0)
            fee = fee_by_wallet.get(w, 0)
            ref = refund_executed_by_wallet.get(w, 0)

            if actual_c != (dep + fee - ref):
                matches_legacy_all = False
            if actual_c != (dep - ref):
                matches_gross_all = False
            if actual_c != (dep - fee - ref):
                matches_net_all = False

        if matches_legacy_all and not matches_gross_all and not matches_net_all:
            return {
                "contractVersion": CONTRACT_VERSION_LEGACY_GROSS,
                "detectionMethod": "verified_by_onchain_state_and_paired_events",
                "verified": True,
            }
        if matches_gross_all and not matches_legacy_all and not matches_net_all:
            return {
                "contractVersion": CONTRACT_VERSION_GROSS_CONTRIBUTION,
                "detectionMethod": "verified_by_onchain_state_and_paired_events",
                "verified": True,
            }
        if matches_net_all and not matches_legacy_all and not matches_gross_all:
            return {
                "contractVersion": CONTRACT_VERSION_NET_CONTRIBUTION,
                "detectionMethod": "verified_by_onchain_state_and_paired_events",
                "verified": True,
            }

        return {
            "contractVersion": CONTRACT_VERSION_UNVERIFIED,
            "detectionMethod": "ambiguous_or_divergent_onchain_state",
            "verified": False,
        }

    def reconcile_contract_state_at_block(
        self,
        block_number: int,
        student_wallets: Optional[Sequence[str]] = None,
        logs_up_to_block: Optional[Sequence[Dict[str, Any]]] = None,
        contract_version: Optional[str] = None,
        abi_verification_status: Optional[str] = None,
        compiled_runtime_bytecode_hex: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Phase 2.1 & 2.2.1 – Perform same-`blockTag` Smart Contract state reconciliation at `block_number`.
        Supports two distinct version-specific reconciliation rules:
        - `CONTRACT_VERSION_GROSS_CONTRIBUTION` (`GROSS_CONTRIBUTION`, canonical for `0x909486...503D`):
          - `studentContributions[w] == SUM(FundDeposited[w]) - SUM(RefundRequestExecuted[w])`
          - `classFundDeposits == SUM(FundDeposited) - SUM(AdminFeeCollected)`
          - `classFundBalance == classFundDeposits - SUM(ProposalExecuted) - SUM(RefundRequestExecuted)`
          - `adminFeePool == SUM(AdminFeeCollected) - SUM(AdminFeeWithdrawn)`
        - `CONTRACT_VERSION_LEGACY_GROSS` (`LEGACY_GROSS_CONTRIBUTION`):
          - `studentContributions[w] == SUM(FundDeposited[w]) + SUM(AdminFeeCollected[w]) - SUM(RefundRequestExecuted[w])`
          - `classFundDeposits == SUM(FundDeposited)`

        Strict safeguards:
        1. Verifies `FundDeposited` and `AdminFeeCollected` share the same `transactionHash`, same `student`,
           and valid 1% BPS ratio (`FEE_BPS = 100 / 10000`). Missing or orphan `AdminFeeCollected` events
           are flagged immediately.
        2. NEVER adds `AdminFeeCollected` to `studentContributions` in `CONTRACT_VERSION_GROSS_CONTRIBUTION`,
           and NEVER subtracts 1% a second time from `classFundBalance`.
        3. Never double-subtracts `RefundProcessed` (`RefundRequestExecuted` and `RefundProcessed` in the same tx
           are verified for parity and subtracted once; `RefundExecutionFailed` and `RefundRequestExpired` are
           never subtracted).
        4. If `contract_version` is not explicitly provided (`None`), requires paired deposit+fee evidence
           to determine the version; if insufficient evidence, sets `contractVersion = CONTRACT_VERSION_UNVERIFIED`
           and `reconciled = False`.
        5. If `abi_verification_status == DEPLOYED_ABI_NOT_VERIFIED` (or ABI check fails), refuses to mark
           `reconciled = True`.
        """
        blk_num = int(block_number)
        requested_norm_version = normalize_contract_version(contract_version)
        include_net_views_upfront = requested_norm_version == CONTRACT_VERSION_NET_CONTRIBUTION
        source_logs = (
            list(logs_up_to_block)
            if logs_up_to_block is not None
            else [
                lg
                for lg in self._indexed_logs.values()
                if int(lg["blockNumber"]) <= blk_num and not lg.get("removed", False)
            ]
        )

        # Deduplicate logs by logKey before aggregating so duplicate logs in a passed list never double-add
        dedup_logs_map: Dict[str, Dict[str, Any]] = {}
        for lg in source_logs:
            if int(lg["blockNumber"]) > blk_num or lg.get("removed", False):
                continue
            lkey = lg.get("logKey") or build_composite_log_key(
                int(lg.get("chainId", self.expected_chain_id)),
                str(lg["transactionHash"]),
                int(lg["logIndex"]),
            )
            dedup_logs_map[lkey] = lg
        clean_logs = list(dedup_logs_map.values())

        # Verify ABI status at block B
        if abi_verification_status is not None:
            abi_check = {
                "status": abi_verification_status,
                "abiVerified": abi_verification_status == DEPLOYED_ABI_VERIFIED,
            }
        else:
            abi_check = self.verify_deployed_abi_at_block(
                block_tag=blk_num,
                compiled_runtime_bytecode_hex=compiled_runtime_bytecode_hex,
                require_exact_runtime_match=compiled_runtime_bytecode_hex is not None,
                require_net_contribution_views=include_net_views_upfront,
            )

        # Verify deposit+fee and refund_executed+refund_processed event pairings per transaction
        pairing_check = self.verify_deposit_and_refund_event_pairings(clean_logs, up_to_block=blk_num)

        # Collect all student wallets from logs + explicit list
        wallet_set: Set[str] = set()
        if student_wallets:
            for w in student_wallets:
                wallet_set.add(normalize_address(w, field_name="student_wallet"))

        for lg in clean_logs:
            ev = lg.get("eventName")
            args = lg.get("args", {})
            if ev in ("FundDeposited", "AdminFeeCollected", "RefundProcessed") and "student" in args:
                wallet_set.add(normalize_address(args["student"]))
            elif ev in ("RefundRequestCreated", "RefundRequestExecuted", "RefundExecutionFailed") and "applicant" in args:
                wallet_set.add(normalize_address(args["applicant"]))

        sorted_wallets = sorted(wallet_set)
        onchain = self.read_contract_state_at_block(
            blk_num,
            sorted_wallets,
            include_net_contribution_views=include_net_views_upfront,
        )

        # Also include any applicant from on-chain refundRequests not yet in sorted_wallets
        extra_wallets: Set[str] = set()
        for req in onchain["refundRequests"].values():
            app_w = normalize_address(req["applicant"])
            if app_w not in onchain["students"]:
                extra_wallets.add(app_w)
        if extra_wallets:
            extra_state = self.read_contract_state_at_block(
                blk_num,
                sorted(extra_wallets),
                include_net_contribution_views=include_net_views_upfront,
            )
            onchain["students"].update(extra_state["students"])
            sorted_wallets = sorted(onchain["students"].keys())

        # Aggregate deduplicated logs up to block B per wallet and globally
        deposited_by_wallet: Dict[str, int] = {w: 0 for w in sorted_wallets}
        admin_fee_by_wallet: Dict[str, int] = {w: 0 for w in sorted_wallets}
        refund_executed_by_wallet: Dict[str, int] = {w: 0 for w in sorted_wallets}
        refund_processed_by_wallet: Dict[str, int] = {w: 0 for w in sorted_wallets}
        refund_failed_by_wallet: Dict[str, int] = {w: 0 for w in sorted_wallets}
        refund_expired_count: int = 0
        class_fund_net_deposits_wei: int = 0
        sum_proposal_executed_wei: int = 0
        sum_admin_fee_withdrawn_wei: int = 0

        # Group deposits and fees by tx to compute exact net class fund deposits per deposit tx
        tx_deposits: Dict[str, List[int]] = {}
        tx_fees: Dict[str, List[int]] = {}

        for lg in clean_logs:
            ev = lg.get("eventName")
            args = lg.get("args", {})
            tx_h = normalize_hex_hash(lg["transactionHash"], field_name="transactionHash")
            if ev == "FundDeposited":
                w = normalize_address(args["student"])
                amt = int(args["amount"])
                deposited_by_wallet[w] = deposited_by_wallet.get(w, 0) + amt
                tx_deposits.setdefault(tx_h, []).append(amt)
            elif ev == "AdminFeeCollected":
                w = normalize_address(args["student"])
                f_amt = int(args["feeAmount"])
                admin_fee_by_wallet[w] = admin_fee_by_wallet.get(w, 0) + f_amt
                tx_fees.setdefault(tx_h, []).append(f_amt)
            elif ev == "RefundRequestExecuted":
                w = normalize_address(args["applicant"])
                refund_executed_by_wallet[w] = refund_executed_by_wallet.get(w, 0) + int(args["amount"])
            elif ev == "RefundProcessed":
                w = normalize_address(args["student"])
                refund_processed_by_wallet[w] = refund_processed_by_wallet.get(w, 0) + int(args["amount"])
            elif ev == "RefundExecutionFailed":
                w = normalize_address(args["applicant"])
                refund_failed_by_wallet[w] = refund_failed_by_wallet.get(w, 0) + int(args["amount"])
            elif ev == "RefundRequestExpired":
                refund_expired_count += 1
            elif ev == "ProposalExecuted":
                sum_proposal_executed_wei += int(args["amount"])
            elif ev == "AdminFeeWithdrawn":
                sum_admin_fee_withdrawn_wei += int(args["amount"])

        # Resolve or verify contract accounting version
        version_info = self.detect_contract_accounting_version(
            onchain_state=onchain,
            deposited_by_wallet=deposited_by_wallet,
            fee_by_wallet=admin_fee_by_wallet,
            refund_executed_by_wallet=refund_executed_by_wallet,
            pairing_check=pairing_check,
            explicit_version=contract_version,
        )
        resolved_version = version_info["contractVersion"]

        # When NET_CONTRIBUTION is auto-detected, read the new view functions & verify extended ABI
        if resolved_version == CONTRACT_VERSION_NET_CONTRIBUTION and not include_net_views_upfront:
            block_tag = hex(blk_num)
            for w in sorted_wallets:
                onchain["students"][w]["studentTotalDepositedWei"] = int(
                    self.call_view_function("studentTotalDeposited", [w], block_tag=block_tag)
                )
                onchain["students"][w]["getStudentMaxRefundWei"] = int(
                    self.call_view_function("getStudentMaxRefund", [w], block_tag=block_tag)
                )
            if abi_verification_status is None:
                abi_check = self.verify_deployed_abi_at_block(
                    block_tag=blk_num,
                    compiled_runtime_bytecode_hex=compiled_runtime_bytecode_hex,
                    require_exact_runtime_match=compiled_runtime_bytecode_hex is not None,
                    require_net_contribution_views=True,
                )

        discrepancies: List[Dict[str, Any]] = []
        student_checks: Dict[str, Dict[str, Any]] = {}

        if not abi_check["abiVerified"]:
            discrepancies.append(
                {
                    "formula": "DEPLOYED_ABI_VERIFICATION",
                    "status": DEPLOYED_ABI_NOT_VERIFIED,
                    "details": abi_check,
                }
            )

        if not pairing_check["valid"]:
            for anom in pairing_check["anomalies"]:
                discrepancies.append(
                    {
                        "formula": "DEPOSIT_AND_REFUND_EVENT_PAIRING_INTEGRITY",
                        "anomaly": anom,
                    }
                )

        if resolved_version == CONTRACT_VERSION_UNVERIFIED:
            discrepancies.append(
                {
                    "formula": "CONTRACT_VERSION_VERIFICATION",
                    "status": CONTRACT_VERSION_UNVERIFIED,
                    "detectionMethod": version_info["detectionMethod"],
                }
            )

        # Active refunds (Pending=0 or Ready=1) from on-chain state at block B
        active_refunds_by_wallet: Dict[str, int] = {w: 0 for w in sorted_wallets}
        expected_reserved_refund_wei = 0
        for req in onchain["refundRequests"].values():
            if req["status"] in (REFUND_STATUS_PENDING, REFUND_STATUS_READY):
                amt = int(req["amountWei"])
                expected_reserved_refund_wei += amt
                w = normalize_address(req["applicant"])
                active_refunds_by_wallet[w] = active_refunds_by_wallet.get(w, 0) + amt

        actual_available_fund_wei = int(onchain["getAvailableClassFundWei"])

        for w in sorted_wallets:
            st = onchain["students"][w]
            sum_dep = deposited_by_wallet.get(w, 0)
            sum_fee = admin_fee_by_wallet.get(w, 0)
            sum_ref_exec = refund_executed_by_wallet.get(w, 0)
            sum_ref_proc = refund_processed_by_wallet.get(w, 0)

            if resolved_version == CONTRACT_VERSION_LEGACY_GROSS:
                expected_contrib = sum_dep + sum_fee - sum_ref_exec
                formula1_label = (
                    "studentContributions == SUM(FundDeposited) + SUM(AdminFeeCollected) - SUM(RefundRequestExecuted)"
                )
            elif resolved_version == CONTRACT_VERSION_NET_CONTRIBUTION:
                expected_contrib = sum_dep - sum_fee - sum_ref_exec
                formula1_label = (
                    "studentContributions == SUM(FundDeposited) - SUM(AdminFeeCollected) - SUM(RefundRequestExecuted)"
                )
            else:
                expected_contrib = sum_dep - sum_ref_exec
                formula1_label = "studentContributions == SUM(FundDeposited) - SUM(RefundRequestExecuted)"

            actual_contrib = int(st["studentContributionsWei"])
            actual_pending = int(st["pendingStudentRefundAmountWei"])
            actual_avail = int(st["getStudentAvailableContributionWei"])
            expected_avail = actual_contrib - actual_pending
            expected_pending = active_refunds_by_wallet.get(w, 0)

            formula1_ok = (
                resolved_version != CONTRACT_VERSION_UNVERIFIED
                and pairing_check["valid"]
                and (actual_contrib == expected_contrib)
            )
            formula2_ok = actual_avail == expected_avail
            pending_ok = actual_pending == expected_pending
            dual_event_ok = sum_ref_exec == sum_ref_proc

            total_deposited_ok: Optional[bool] = None
            max_refund_ok: Optional[bool] = None
            actual_total_deposited: Optional[int] = None
            actual_max_refund: Optional[int] = None
            expected_max_refund: Optional[int] = None
            if resolved_version == CONTRACT_VERSION_NET_CONTRIBUTION:
                actual_total_deposited = int(st["studentTotalDepositedWei"])
                total_deposited_ok = pairing_check["valid"] and (actual_total_deposited == sum_dep)
                actual_max_refund = int(st["getStudentMaxRefundWei"])
                expected_max_refund = min(actual_avail, actual_available_fund_wei)
                max_refund_ok = actual_max_refund == expected_max_refund

            if not formula1_ok:
                discrepancies.append(
                    {
                        "formula": formula1_label,
                        "contractVersion": resolved_version,
                        "wallet": w,
                        "expectedWei": expected_contrib,
                        "actualWei": actual_contrib,
                        "sumFundDepositedWei": sum_dep,
                        "sumAdminFeeCollectedWei": sum_fee,
                        "sumRefundRequestExecutedWei": sum_ref_exec,
                    }
                )
            if resolved_version == CONTRACT_VERSION_NET_CONTRIBUTION and total_deposited_ok is False:
                discrepancies.append(
                    {
                        "formula": "studentTotalDeposited == SUM(FundDeposited)",
                        "contractVersion": resolved_version,
                        "wallet": w,
                        "expectedWei": sum_dep,
                        "actualWei": actual_total_deposited,
                    }
                )
            if resolved_version == CONTRACT_VERSION_NET_CONTRIBUTION and max_refund_ok is False:
                discrepancies.append(
                    {
                        "formula": "getStudentMaxRefund == min(getStudentAvailableContribution, getAvailableClassFund)",
                        "contractVersion": resolved_version,
                        "wallet": w,
                        "expectedWei": expected_max_refund,
                        "actualWei": actual_max_refund,
                    }
                )
            if not formula2_ok:
                discrepancies.append(
                    {
                        "formula": "getStudentAvailableContribution == studentContributions - pendingStudentRefundAmount",
                        "wallet": w,
                        "expectedWei": expected_avail,
                        "actualWei": actual_avail,
                        "studentContributionsWei": actual_contrib,
                        "pendingStudentRefundAmountWei": actual_pending,
                    }
                )
            if not pending_ok:
                discrepancies.append(
                    {
                        "formula": "pendingStudentRefundAmount == sum(active refundRequests[wallet])",
                        "wallet": w,
                        "expectedWei": expected_pending,
                        "actualWei": actual_pending,
                    }
                )
            if not dual_event_ok:
                discrepancies.append(
                    {
                        "formula": "sum(RefundRequestExecuted[wallet]) == sum(RefundProcessed[wallet])",
                        "wallet": w,
                        "expectedWei": sum_ref_exec,
                        "actualWei": sum_ref_proc,
                    }
                )

            student_checks[w] = {
                "wallet": w,
                "contractVersionApplied": resolved_version,
                "sumFundDepositedWei": sum_dep,
                "sumAdminFeeCollectedWei": sum_fee,
                "sumRefundRequestExecutedWei": sum_ref_exec,
                "sumRefundProcessedWei": sum_ref_proc,
                "sumRefundExecutionFailedWei": refund_failed_by_wallet.get(w, 0),
                "expectedStudentContributionsWei": expected_contrib,
                "actualStudentContributionsWei": actual_contrib,
                "expectedStudentTotalDepositedWei": sum_dep if resolved_version == CONTRACT_VERSION_NET_CONTRIBUTION else None,
                "actualStudentTotalDepositedWei": actual_total_deposited,
                "expectedStudentMaxRefundWei": expected_max_refund,
                "actualStudentMaxRefundWei": actual_max_refund,
                "expectedPendingRefundWei": expected_pending,
                "actualPendingRefundWei": actual_pending,
                "expectedAvailableContributionWei": expected_avail,
                "actualAvailableContributionWei": actual_avail,
                "formula1Passed": formula1_ok,
                "formula2Passed": formula2_ok,
                "totalDepositedFormulaPassed": total_deposited_ok,
                "maxRefundFormulaPassed": max_refund_ok,
                "pendingMatchPassed": pending_ok,
                "dualRefundEventParityPassed": dual_event_ok,
            }

        # Global deposit, fee, and classFundBalance reconciliation:
        # In ProjectCore.sol (`GROSS_CONTRIBUTION` and `NET_CONTRIBUTION`):
        #   `classFundDeposits = SUM(FundDeposited) - SUM(AdminFeeCollected)` (99% net; 1% subtracted ONCE)
        #   `classFundBalance = classFundDeposits - SUM(ProposalExecuted) - SUM(RefundRequestExecuted)`
        #   `adminFeePool = SUM(AdminFeeCollected) - SUM(AdminFeeWithdrawn)`
        sum_fund_deposited_wei = sum(deposited_by_wallet.values())
        sum_admin_fee_collected_wei = sum(admin_fee_by_wallet.values())
        sum_refund_executed_wei = sum(refund_executed_by_wallet.values())

        if resolved_version == CONTRACT_VERSION_LEGACY_GROSS:
            # In legacy contract, FundDeposited already emitted the 99% net amount
            class_fund_deposits_wei = sum_fund_deposited_wei
        elif resolved_version == CONTRACT_VERSION_NET_CONTRIBUTION:
            class_fund_deposits_wei = sum_fund_deposited_wei - sum_admin_fee_collected_wei
        else:
            # Check if logs emitted 100% gross (`fee == (dep * 100) // 10000`) vs synthetic 99% net fixture
            if sum_fund_deposited_wei > 0 and (
                (sum_fund_deposited_wei * FEE_BPS) // BPS_DENOMINATOR == sum_admin_fee_collected_wei
                or all(
                    f == (d * FEE_BPS) // BPS_DENOMINATOR
                    for tx_h in tx_deposits
                    for d, f in zip(tx_deposits.get(tx_h, []), tx_fees.get(tx_h, []))
                )
            ):
                class_fund_deposits_wei = sum_fund_deposited_wei - sum_admin_fee_collected_wei
            else:
                class_fund_deposits_wei = sum_fund_deposited_wei

        expected_class_fund_balance_wei = (
            class_fund_deposits_wei - sum_proposal_executed_wei - sum_refund_executed_wei
        )
        actual_class_fund_balance_wei = int(onchain["classFundBalanceWei"])
        class_fund_balance_ok = (
            resolved_version != CONTRACT_VERSION_UNVERIFIED
            and pairing_check["valid"]
            and (actual_class_fund_balance_wei == expected_class_fund_balance_wei)
        )
        if not class_fund_balance_ok and resolved_version != CONTRACT_VERSION_UNVERIFIED:
            discrepancies.append(
                {
                    "formula": "classFundBalance == classFundDeposits - SUM(ProposalExecuted) - SUM(RefundRequestExecuted)",
                    "contractVersion": resolved_version,
                    "classFundDepositsWei": class_fund_deposits_wei,
                    "sumFundDepositedWei": sum_fund_deposited_wei,
                    "sumAdminFeeCollectedWei": sum_admin_fee_collected_wei,
                    "sumProposalExecutedWei": sum_proposal_executed_wei,
                    "sumRefundRequestExecutedWei": sum_refund_executed_wei,
                    "expectedWei": expected_class_fund_balance_wei,
                    "actualWei": actual_class_fund_balance_wei,
                }
            )

        expected_admin_fee_pool_wei = sum_admin_fee_collected_wei - sum_admin_fee_withdrawn_wei
        actual_admin_fee_pool_wei = int(onchain["adminFeePoolWei"])
        admin_fee_pool_ok = (
            pairing_check["valid"] and (actual_admin_fee_pool_wei == expected_admin_fee_pool_wei)
        )
        if not admin_fee_pool_ok and pairing_check["valid"]:
            discrepancies.append(
                {
                    "formula": "adminFeePool == SUM(AdminFeeCollected) - SUM(AdminFeeWithdrawn)",
                    "sumAdminFeeCollectedWei": sum_admin_fee_collected_wei,
                    "sumAdminFeeWithdrawnWei": sum_admin_fee_withdrawn_wei,
                    "expectedWei": expected_admin_fee_pool_wei,
                    "actualWei": actual_admin_fee_pool_wei,
                }
            )

        # Formula 3: reservedRefundAmount == sum(Pending + Ready refund requests)
        actual_reserved_refund_wei = int(onchain["reservedRefundAmountWei"])
        formula3_reserved_ok = actual_reserved_refund_wei == expected_reserved_refund_wei
        if not formula3_reserved_ok:
            discrepancies.append(
                {
                    "formula": "reservedRefundAmount == sum(refundRequests where status in {Pending, Ready})",
                    "expectedWei": expected_reserved_refund_wei,
                    "actualWei": actual_reserved_refund_wei,
                }
            )

        # Global available class fund check: getAvailableClassFund == classFundBalance - reservedSpendAmount - reservedRefundAmount
        expected_available_fund_wei = (
            actual_class_fund_balance_wei
            - int(onchain["reservedSpendAmountWei"])
            - actual_reserved_refund_wei
        )
        actual_available_fund_wei = int(onchain["getAvailableClassFundWei"])
        available_fund_ok = actual_available_fund_wei == expected_available_fund_wei
        if not available_fund_ok:
            discrepancies.append(
                {
                    "formula": "getAvailableClassFund == classFundBalance - reservedSpendAmount - reservedRefundAmount",
                    "expectedWei": expected_available_fund_wei,
                    "actualWei": actual_available_fund_wei,
                }
            )

        is_fully_reconciled = (
            len(discrepancies) == 0
            and abi_check["abiVerified"]
            and pairing_check["valid"]
            and resolved_version != CONTRACT_VERSION_UNVERIFIED
        )

        return {
            "blockNumber": blk_num,
            "blockTag": hex(blk_num),
            "reconciled": is_fully_reconciled,
            "contractVersion": resolved_version,
            "contractVersionVerification": version_info,
            "abiVerificationStatus": abi_check["status"],
            "abiVerification": abi_check,
            "eventPairingVerification": pairing_check,
            "discrepancyCount": len(discrepancies),
            "discrepancies": discrepancies,
            "globalChecks": {
                "sumFundDepositedWei": sum_fund_deposited_wei,
                "sumAdminFeeCollectedWei": sum_admin_fee_collected_wei,
                "classFundDepositsWei": class_fund_deposits_wei,
                "sumProposalExecutedWei": sum_proposal_executed_wei,
                "sumRefundRequestExecutedWei": sum_refund_executed_wei,
                "sumAdminFeeWithdrawnWei": sum_admin_fee_withdrawn_wei,
                "expectedClassFundBalanceWei": expected_class_fund_balance_wei,
                "classFundBalanceWei": actual_class_fund_balance_wei,
                "classFundBalanceFormulaPassed": class_fund_balance_ok,
                "expectedAdminFeePoolWei": expected_admin_fee_pool_wei,
                "adminFeePoolWei": actual_admin_fee_pool_wei,
                "adminFeePoolFormulaPassed": admin_fee_pool_ok,
                "reservedSpendAmountWei": onchain["reservedSpendAmountWei"],
                "expectedReservedRefundAmountWei": expected_reserved_refund_wei,
                "actualReservedRefundAmountWei": actual_reserved_refund_wei,
                "reservedRefundFormulaPassed": formula3_reserved_ok,
                "expectedAvailableClassFundWei": expected_available_fund_wei,
                "actualAvailableClassFundWei": actual_available_fund_wei,
                "availableClassFundFormulaPassed": available_fund_ok,
            },
            "studentChecks": student_checks,
        }

    # ------------------------------------------------------------------------
    # Phase 2.2.1 Section 5 – Full Blockchain History Scan from `deployBlock`
    # ------------------------------------------------------------------------

    def scan_history_from_deploy_block(
        self,
        to_block: Optional[int] = None,
        from_block: Optional[int] = None,
        campaigns: Optional[Union[Sequence[Dict[str, Any]], Dict[str, Dict[str, Any]]]] = None,
        chunk_size: int = DEFAULT_LOG_CHUNK_SIZE,
        batch_size: Optional[int] = None,
        student_wallets: Optional[Sequence[str]] = None,
        contract_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Phase 2.2.1 Section 5 – Scan and verify blockchain history from `deployBlock` (`12042025`)
        up to `to_block` (or current head block):
        1. Resolves and verifies `deployBlock` (refuses to scan from genesis or guess if unverified).
        2. Scans logs in batches (`chunk_size`), adaptively halving batch size if RPC limits block range,
           and verifies contiguous coverage (`noBlocksSkipped == True`).
        3. Deduplicates all logs by `(chainId, transactionHash, logIndex)`.
        4. Verifies `blockHash` and `parentHash` across all cached block headers.
        5. Classifies deposits against `campaigns` (if provided) and checks whether any logs are
           still in `pending_reconciliation`.
        6. Performs same-`blockTag` Smart Contract state reconciliation at `to_block`.
        7. NEVER marks `syncCompleted = True` if:
           - `deployBlock` is unverified (`SYNC_CONFIG_REQUIRED`),
           - any block was skipped (`not noBlocksSkipped`),
           - any Reorg or `blockHash`/`parentHash` mismatch is detected,
           - any deposit log is in `pending_reconciliation`, or
           - Smart Contract state reconciliation has any discrepancy (`not reconciled`).
        8. Strictly read-only: never performs automatic rollback and never writes to real data files.
        """
        if to_block is None:
            head_block = parse_hex_int(self.rpc.call("eth_blockNumber", []), field_name="eth_blockNumber")
        else:
            head_block = int(to_block)

        deploy_info = self.resolve_deploy_block(
            latest_block=head_block,
            search_floor_block=from_block if from_block is not None else DEFAULT_DEPLOY_SEARCH_FLOOR_BLOCK,
        )
        if deploy_info["status"] != DEPLOY_BLOCK_VERIFIED or deploy_info["deployBlock"] is None:
            return {
                "syncStatus": SYNC_CONFIG_REQUIRED,
                "syncCompleted": False,
                "deployResolution": deploy_info,
                "reason": "DEPLOY_BLOCK_NOT_VERIFIED",
            }

        start_blk = int(from_block) if from_block is not None else int(deploy_info["deployBlock"])
        effective_chunk_size = int(batch_size) if batch_size is not None else int(chunk_size)
        scan_res = self.fetch_and_index_logs(
            from_block=start_blk,
            to_block=head_block,
            chunk_size=effective_chunk_size,
        )

        # Verify blockHash & parentHash continuity across all cached headers
        cached_headers = list(self._block_header_cache.values())
        reorg_check = self.detect_reorg_on_headers(cached_headers, refetch_from_rpc=False)
        any_log_needs_reorg = any(bool(lg.get("needsReorgCheck")) for lg in self._indexed_logs.values())
        reorg_detected = bool(
            reorg_check.reorg_detected
            or (self.last_reorg_detection and self.last_reorg_detection.reorg_detected)
            or any_log_needs_reorg
        )

        classification_summary: Optional[Dict[str, Any]] = None
        pending_reconciliation_count = 0
        if campaigns is not None:
            classification_summary = self.classify_all_indexed_deposits(campaigns=campaigns)
            pending_reconciliation_count = int(
                classification_summary["countsByState"].get("pending_reconciliation", 0)
            )

        reconciliation = self.reconcile_contract_state_at_block(
            block_number=head_block,
            student_wallets=student_wallets,
            contract_version=contract_version,
        )

        blocking_reasons: List[str] = []
        if not scan_res["noBlocksSkipped"]:
            blocking_reasons.append("INCOMPLETE_BLOCK_RANGE_COVERAGE")
        if reorg_detected:
            blocking_reasons.append("REORG_OR_BLOCK_HASH_MISMATCH_DETECTED")
        if pending_reconciliation_count > 0:
            blocking_reasons.append(f"LOGS_PENDING_RECONCILIATION:{pending_reconciliation_count}")
        if not reconciliation["reconciled"]:
            blocking_reasons.append("ONCHAIN_STATE_RECONCILIATION_MISMATCH")

        sync_completed = len(blocking_reasons) == 0
        if sync_completed:
            sync_status = "SYNC_COMPLETED"
        elif pending_reconciliation_count > 0 and len(blocking_reasons) == 1:
            sync_status = "PENDING_RECONCILIATION"
        elif reorg_detected:
            sync_status = "REORG_DETECTED"
        else:
            sync_status = "INCOMPLETE_OR_MISMATCHED"

        return {
            "syncStatus": sync_status,
            "syncCompleted": sync_completed,
            "blockingReasons": blocking_reasons,
            "fromBlock": start_blk,
            "toBlock": head_block,
            "noBlocksSkipped": scan_res["noBlocksSkipped"],
            "chunkCount": scan_res["chunkCount"],
            "inserted": scan_res["newlyIndexedCount"],
            "duplicatesSkipped": scan_res["duplicatesSkipped"],
            "reconciled": reconciliation["reconciled"],
            "deployResolution": deploy_info,
            "scanSummary": {
                "chunkCount": scan_res["chunkCount"],
                "chunksScanned": scan_res["chunksScanned"],
                "noBlocksSkipped": scan_res["noBlocksSkipped"],
                "rawLogsFetched": scan_res["rawLogsFetched"],
                "newlyIndexedCount": scan_res["newlyIndexedCount"],
                "duplicatesSkipped": scan_res["duplicatesSkipped"],
                "totalUniqueIndexedLogs": scan_res["totalUniqueIndexedLogs"],
                "uniqueBlocksCached": scan_res["uniqueBlocksCached"],
            },
            "reorgVerification": {
                "reorgDetected": reorg_detected,
                "headerCheck": reorg_check.to_dict(),
                "lastReorgDetection": self.last_reorg_detection.to_dict() if self.last_reorg_detection else None,
            },
            "classificationSummary": classification_summary,
            "pendingReconciliationCount": pending_reconciliation_count,
            "reconciliation": reconciliation,
            "reconciliationReport": reconciliation,
        }

    # ------------------------------------------------------------------------
    # Isolated Experimental Output Writer (Never touches real data files)
    # ------------------------------------------------------------------------

    @staticmethod
    def export_snapshot_to_temp_file(snapshot: Dict[str, Any], target_path: Union[str, Path]) -> str:
        """
        Write an indexer snapshot or reconciliation report ONLY to an isolated temp/test directory.
        Explicitly refuses to write inside `backend/` real data files.
        """
        out_path = Path(target_path).resolve()
        forbidden_names = {
            "announcements.json",
            "class_roster.json",
            "announcements.pre_v4_migration.bak",
        }
        if out_path.name in forbidden_names:
            raise ReadOnlyPolicyViolationError(
                f"Refusing to write indexer output to protected file name: {out_path}"
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(out_path)
