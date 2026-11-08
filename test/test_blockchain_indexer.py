"""
Unit and Integration Test Suite for Phase 2 – Blockchain RPC Indexer (Read-Only Implementation).

All tests run strictly against mock/fixture RPC transports and isolated `tempfile.TemporaryDirectory()`
instances. Never sends transactions, never mutates real data files (`backend/announcements.json`
or `backend/class_roster.json`), and never sets `ALLOW_REAL_DATA_MUTATION=1`.

Covers all 14 mandatory Phase 2 test scenarios + fraud/edge cases:
1. Chain ID verification (`11155111` vs wrong Chain ID).
2. Wrong contract address (EOA / empty bytecode `0x` / malformed address).
3. Wrong ABI / nonexistent event rejection (`RefundApproved`, `RefundReady`).
4. Event parsing (`FundDeposited`, `AdminFeeCollected`, `RefundRequestCreated`, `RefundRequestReady`,
   `RefundRequestExecuted`, `RefundExecutionFailed`, `RefundRequestExpired`, `RefundProcessed`, etc.).
5. Block timestamp fetching & block header caching (1 RPC call per unique block number).
6. Log deduplication by `(chainId, transactionHash, logIndex)` while preserving multi-event transactions.
7. Transaction clearly inside a campaign (`classified_by_block_timestamp`).
8. Transaction within `±12s` boundary or shared second `1793619753` (`pending_reconciliation`, never auto-confirmed).
9. Transaction outside all campaigns (`unallocated`).
10. Exact integer Wei preservation (odd 1-wei / 18-decimal values, zero float precision loss).
11. Same-`blockTag` Smart Contract reconciliation (all 3 formulas verified at block `B`, plus mismatch detection).
12. Simulated `blockHash` change / `parentHash` linkage break (Reorg detection & flagging affected range).
13. RPC timeout and exponential backoff retry recovery.
14. RPC returning malformed/invalid JSON-RPC data or attempting forbidden mutating methods.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from eth_abi import encode as abi_encode
from eth_utils import keccak, to_checksum_address

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from accounting_engine import migrate_v1_to_v2_store
from blockchain_indexer import (
    CONTRACT_VERSION_GROSS_CONTRIBUTION,
    CONTRACT_VERSION_LEGACY_GROSS,
    CONTRACT_VERSION_NET_CONTRIBUTION,
    CONTRACT_VERSION_NEW_NET,
    CONTRACT_VERSION_UNVERIFIED,
    DEFAULT_CONTRACT_ADDRESS,
    DEFAULT_CONTRACT_CREATOR,
    DEFAULT_DEPLOY_BLOCK,
    DEFAULT_DEPLOY_BLOCK_HASH,
    DEFAULT_DEPLOYMENT_TX_HASH,
    DEPLOY_BLOCK_VERIFIED,
    DEPLOYED_ABI_NOT_VERIFIED,
    DEPLOYED_ABI_VERIFIED,
    EXPECTED_SEPOLIA_CHAIN_ID,
    PROJECT_CORE_ABI,
    REFUND_STATUS_CANCELLED,
    REFUND_STATUS_EXECUTED,
    REFUND_STATUS_EXPIRED,
    REFUND_STATUS_PENDING,
    REFUND_STATUS_READY,
    SHARED_SECOND_BOUNDARY_TS,
    SYNC_CONFIG_REQUIRED,
    BlockchainRPCIndexer,
    ChainIdMismatchError,
    InvalidContractABIError,
    InvalidContractAddressError,
    JsonRpcClient,
    ReadOnlyPolicyViolationError,
    RpcTransportError,
    build_composite_log_key,
    load_deployment_config,
    normalize_contract_version,
    validate_contract_abi,
    wei_to_eth_display,
)

REAL_ANNOUNCEMENTS_PATH = BACKEND_DIR / "announcements.json"
REAL_ROSTER_PATH = BACKEND_DIR / "class_roster.json"
PRE_V4_BACKUP_PATH = BACKEND_DIR / "announcements.pre_v4_migration.bak"

STUDENT_A = to_checksum_address("0x78567a377559f0cb30173f93869326a82320159a")
STUDENT_B = to_checksum_address("0xf5d971952dbdf69058a28d23110381d96b00cb50")
STUDENT_C = to_checksum_address("0x7af21f18defda4a141bad89681c0d4767a42333c")


def _sha256_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _topic_Hash(sig: str) -> str:
    return "0x" + keccak(text=sig).hex()


def _topic_addr(addr: str) -> str:
    return "0x" + abi_encode(["address"], [to_checksum_address(addr)]).hex()


def _topic_u256(val: int) -> str:
    return "0x" + abi_encode(["uint256"], [int(val)]).hex()


def _block_hash(num: int, suffix: str = "a") -> str:
    body = f"{num:016x}" + (suffix * 48)
    return "0x" + body[:64].lower()


def _tx_hash(seed: int) -> str:
    return "0x" + f"{seed:064x}"


class MockSepoliaRpcRouter:
    """
    Deterministic in-memory JSON-RPC router for testing `BlockchainRPCIndexer`
    without network flakiness or mutating operations.
    """

    def __init__(
        self,
        chain_id: int = EXPECTED_SEPOLIA_CHAIN_ID,
        contract_address: str = DEFAULT_CONTRACT_ADDRESS,
        deploy_block: int = 12047880,
        latest_block: int = 12048000,
    ) -> None:
        self.chain_id = chain_id
        self.contract_address = to_checksum_address(contract_address)
        self.deploy_block = deploy_block
        self.latest_block = latest_block
        self.bytecode = "0x608060405234801561001057600080fd5b50"
        self.pruned_before_block: Optional[int] = None
        self.blocks: Dict[int, Dict[str, Any]] = {}
        self.receipts: Dict[str, Dict[str, Any]] = {}
        self.logs: List[Dict[str, Any]] = []
        # On-chain state snapshots keyed by blockTag hex (`0x...`) or `'latest'`
        self.state_by_block: Dict[str, Dict[str, Any]] = {}
        self.method_counts: Dict[str, int] = {}
        self.get_block_calls_by_number: Dict[int, int] = {}

    def seed_linear_blocks(
        self, start_block: int, end_block: int, base_timestamp: int, step_seconds: int = 12
    ) -> None:
        prev_hash = _block_hash(start_block - 1, "0")
        for b in range(start_block, end_block + 1):
            b_hash = _block_hash(b, "a")
            ts = base_timestamp + (b - start_block) * step_seconds
            self.blocks[b] = {
                "number": hex(b),
                "hash": b_hash,
                "parentHash": prev_hash,
                "timestamp": hex(ts),
            }
            prev_hash = b_hash

    def seed_deployment_receipt(self, deploy_block: int, tx_hash: str) -> None:
        norm_tx = tx_hash.lower()
        if deploy_block not in self.blocks:
            self.seed_linear_blocks(deploy_block, deploy_block, base_timestamp=1774000000)
        self.blocks[deploy_block]["transactions"] = [
            {
                "hash": norm_tx,
                "from": STUDENT_A,
                "to": None,
            }
        ]
        self.receipts[norm_tx] = {
            "transactionHash": norm_tx,
            "blockNumber": hex(deploy_block),
            "blockHash": self.blocks[deploy_block]["hash"],
            "contractAddress": self.contract_address,
            "status": "0x1",
        }

    def __call__(self, rpc_url: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        method = payload.get("method", "")
        params = payload.get("params", [])
        req_id = payload.get("id", 1)
        self.method_counts[method] = self.method_counts.get(method, 0) + 1

        if method == "eth_chainId":
            return {"jsonrpc": "2.0", "id": req_id, "result": hex(self.chain_id)}

        if method == "eth_blockNumber":
            return {"jsonrpc": "2.0", "id": req_id, "result": hex(self.latest_block)}

        if method == "eth_getCode":
            addr = to_checksum_address(params[0])
            tag = params[1] if len(params) > 1 else "latest"
            blk_num = self.latest_block if tag == "latest" else int(tag, 16)
            if self.pruned_before_block is not None and blk_num < self.pruned_before_block:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32000,
                        "message": f"historical state at block {blk_num} is not available",
                    },
                }
            if addr.lower() != self.contract_address.lower() or blk_num < self.deploy_block:
                return {"jsonrpc": "2.0", "id": req_id, "result": "0x"}
            return {"jsonrpc": "2.0", "id": req_id, "result": self.bytecode}

        if method == "eth_getTransactionReceipt":
            tx_h = str(params[0]).lower()
            return {"jsonrpc": "2.0", "id": req_id, "result": copy.deepcopy(self.receipts.get(tx_h))}

        if method == "eth_getBlockByNumber":
            tag = params[0]
            blk_num = self.latest_block if tag == "latest" else int(tag, 16)
            self.get_block_calls_by_number[blk_num] = self.get_block_calls_by_number.get(blk_num, 0) + 1
            if blk_num not in self.blocks:
                # Auto-synthesize deterministic header if not explicitly seeded
                parent_h = self.blocks.get(blk_num - 1, {}).get("hash", _block_hash(blk_num - 1, "0"))
                self.blocks[blk_num] = {
                    "number": hex(blk_num),
                    "hash": _block_hash(blk_num, "a"),
                    "parentHash": parent_h,
                    "timestamp": hex(1774000000 + blk_num * 12),
                }
            return {"jsonrpc": "2.0", "id": req_id, "result": copy.deepcopy(self.blocks[blk_num])}

        if method == "eth_getLogs":
            flt = params[0] if params else {}
            from_b = int(flt.get("fromBlock", "0x0"), 16)
            to_b = int(flt.get("toBlock", hex(self.latest_block)), 16)
            max_blocks = getattr(self, "max_blocks_per_query", None)
            if max_blocks is not None and (to_b - from_b + 1) > int(max_blocks):
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32005, "message": "eth_getLogs block range limit exceeded"},
                }
            addr_flt = flt.get("address", "").lower()
            topics_flt = flt.get("topics")

            matched: List[Dict[str, Any]] = []
            for lg in self.logs:
                b_num = int(lg["blockNumber"], 16)
                if b_num < from_b or b_num > to_b:
                    continue
                if addr_flt and lg["address"].lower() != addr_flt:
                    continue
                if topics_flt and len(topics_flt) > 0 and topics_flt[0] is not None:
                    allowed_t0 = [t.lower() for t in topics_flt[0]]
                    if lg["topics"][0].lower() not in allowed_t0:
                        continue
                matched.append(copy.deepcopy(lg))
            return {"jsonrpc": "2.0", "id": req_id, "result": matched}

        if method == "eth_call":
            call_obj = params[0]
            tag = params[1] if len(params) > 1 else "latest"
            state = self.state_by_block.get(tag) or self.state_by_block.get("latest")
            if state is None:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": f"No state mocked for tag {tag}"},
                }
            data_hex = call_obj["data"].lower()
            selector = data_hex[:10]
            arg_bytes = bytes.fromhex(data_hex[10:])
            encoded_out = self._dispatch_eth_call(selector, arg_bytes, state)
            return {"jsonrpc": "2.0", "id": req_id, "result": "0x" + encoded_out.hex()}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method {method} not found"},
        }

    @staticmethod
    def _dispatch_eth_call(selector: str, arg_bytes: bytes, state: Dict[str, Any]) -> bytes:
        def sel(sig: str) -> str:
            return "0x" + keccak(text=sig)[:4].hex()

        if selector == sel("classFundBalance()"):
            return abi_encode(["uint256"], [int(state.get("classFundBalance", 0))])
        if selector == sel("adminFeePool()"):
            return abi_encode(["uint256"], [int(state.get("adminFeePool", 0))])
        if selector == sel("reservedSpendAmount()"):
            return abi_encode(["uint256"], [int(state.get("reservedSpendAmount", 0))])
        if selector == sel("reservedRefundAmount()"):
            return abi_encode(["uint256"], [int(state.get("reservedRefundAmount", 0))])
        if selector == sel("getAvailableClassFund()"):
            return abi_encode(["uint256"], [int(state.get("getAvailableClassFund", 0))])
        if selector == sel("refundRequestCount()"):
            reqs = state.get("refundRequests", {})
            return abi_encode(["uint256"], [len(reqs)])
        if selector == sel("getRefundRequest(uint256)"):
            refund_id = int.from_bytes(arg_bytes[:32], "big")
            r = state["refundRequests"][refund_id]
            return abi_encode(
                ["address", "uint256", "string", "uint256", "uint256", "uint256", "uint256", "uint8"],
                [
                    to_checksum_address(r["applicant"]),
                    int(r["amount"]),
                    str(r.get("reason", "")),
                    int(r.get("yesVotes", 0)),
                    int(r.get("noVotes", 0)),
                    int(r.get("createdAt", 0)),
                    int(r.get("deadline", 0)),
                    int(r["status"]),
                ],
            )
        if selector in (sel("studentContributions(address)"), sel("getStudentContribution(address)")):
            addr = to_checksum_address("0x" + arg_bytes[12:32].hex())
            val = state.get("studentContributions", {}).get(addr, 0)
            return abi_encode(["uint256"], [int(val)])
        if selector == sel("studentTotalDeposited(address)"):
            addr = to_checksum_address("0x" + arg_bytes[12:32].hex())
            val = state.get("studentTotalDeposited", {}).get(addr, 0)
            return abi_encode(["uint256"], [int(val)])
        if selector == sel("pendingStudentRefundAmount(address)"):
            addr = to_checksum_address("0x" + arg_bytes[12:32].hex())
            val = state.get("pendingStudentRefundAmount", {}).get(addr, 0)
            return abi_encode(["uint256"], [int(val)])
        if selector == sel("getStudentAvailableContribution(address)"):
            addr = to_checksum_address("0x" + arg_bytes[12:32].hex())
            val = state.get("getStudentAvailableContribution", {}).get(addr, 0)
            return abi_encode(["uint256"], [int(val)])
        if selector == sel("getStudentMaxRefund(address)"):
            addr = to_checksum_address("0x" + arg_bytes[12:32].hex())
            val = state.get("getStudentMaxRefund", {}).get(addr, 0)
            return abi_encode(["uint256"], [int(val)])

        raise RuntimeError(f"Unhandled eth_call selector {selector}")


class TestBlockchainRPCIndexerPhase2(unittest.TestCase):
    """
    Comprehensive Test Suite for Phase 2 Read-Only Blockchain RPC Indexer.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.initial_hashes = {
            "announcements": _sha256_file(REAL_ANNOUNCEMENTS_PATH),
            "roster": _sha256_file(REAL_ROSTER_PATH),
            "pre_v4_bak": _sha256_file(PRE_V4_BACKUP_PATH),
        }

    @classmethod
    def tearDownClass(cls) -> None:
        # Verify real files were never modified during the entire test run
        after_hashes = {
            "announcements": _sha256_file(REAL_ANNOUNCEMENTS_PATH),
            "roster": _sha256_file(REAL_ROSTER_PATH),
            "pre_v4_bak": _sha256_file(PRE_V4_BACKUP_PATH),
        }
        assert cls.initial_hashes == after_hashes, (
            f"SAFETY VIOLATION: Real data files changed during Phase 2 tests! "
            f"Before={cls.initial_hashes}, After={after_hashes}"
        )

    def setUp(self) -> None:
        self.temp_dir_obj = tempfile.TemporaryDirectory(prefix="kts_phase2_indexer_")
        self.temp_dir = Path(self.temp_dir_obj.name)
        self.base_ts = 1774000000
        self.router = MockSepoliaRpcRouter()
        self.router.seed_linear_blocks(12047880, 12047940, base_timestamp=self.base_ts, step_seconds=12)
        self.rpc_client = JsonRpcClient(
            rpc_url="https://mock-sepolia.local",
            timeout_seconds=5.0,
            max_retries=3,
            retry_backoff_seconds=0.0,
            transport_fn=self.router,
        )
        self.indexer = BlockchainRPCIndexer(rpc_client=self.rpc_client)

    def tearDown(self) -> None:
        self.temp_dir_obj.cleanup()

    # ------------------------------------------------------------------------
    # Test 1: Chain ID Verification
    # ------------------------------------------------------------------------

    def test_01_verify_chain_id_sepolia_and_reject_wrong_chain(self) -> None:
        info = self.indexer.verify_network_and_contract()
        self.assertEqual(info["chainId"], EXPECTED_SEPOLIA_CHAIN_ID)
        self.assertEqual(info["contractAddress"], DEFAULT_CONTRACT_ADDRESS)
        self.assertGreater(info["bytecodeLengthBytes"], 0)

        # Simulate wrong chain ID (e.g. Ethereum Mainnet = 1)
        self.router.chain_id = 1
        with self.assertRaises(ChainIdMismatchError):
            self.indexer.verify_network_and_contract()

    # ------------------------------------------------------------------------
    # Test 2: Wrong Contract Address (EOA / Empty Bytecode / Malformed)
    # ------------------------------------------------------------------------

    def test_02_reject_wrong_or_undeployed_contract_address(self) -> None:
        with self.assertRaises(InvalidContractAddressError):
            BlockchainRPCIndexer(rpc_client=self.rpc_client, contract_address="0x12345")

        eoa_address = "0x1111111111111111111111111111111111111111"
        eoa_indexer = BlockchainRPCIndexer(rpc_client=self.rpc_client, contract_address=eoa_address)
        with self.assertRaises(InvalidContractAddressError):
            eoa_indexer.verify_network_and_contract()

        # Also test deploy_block binary search discovery via eth_getCode
        resolved = self.indexer.resolve_deploy_block(latest_block=12047930)
        self.assertEqual(resolved["deployBlock"], 12047880)
        self.assertEqual(resolved["resolutionMethod"], "binary_search_eth_getCode")

    # ------------------------------------------------------------------------
    # Test 3: Wrong ABI & Rejection of Nonexistent Events (`RefundApproved`, `RefundReady`)
    # ------------------------------------------------------------------------

    def test_03_reject_invalid_abi_and_nonexistent_events(self) -> None:
        with self.assertRaises(InvalidContractABIError):
            validate_contract_abi([])

        incomplete_abi = [entry for entry in PROJECT_CORE_ABI if entry.get("name") != "FundDeposited"]
        with self.assertRaises(InvalidContractABIError):
            BlockchainRPCIndexer(rpc_client=self.rpc_client, abi=incomplete_abi)

        # RefundApproved and RefundReady do NOT exist in ProjectCore.sol / ABI
        with self.assertRaises(InvalidContractABIError):
            self.indexer.validate_event_names(["RefundApproved"])
        with self.assertRaises(InvalidContractABIError):
            self.indexer.validate_event_names(["RefundReady"])

        # Actual events RefundRequestVoted and RefundRequestReady MUST be accepted
        valid_specs = self.indexer.validate_event_names(["RefundRequestVoted", "RefundRequestReady"])
        self.assertEqual([s.name for s in valid_specs], ["RefundRequestVoted", "RefundRequestReady"])

    # ------------------------------------------------------------------------
    # Test 4: Parsing All Core Deposit & Refund Lifecycle Events
    # ------------------------------------------------------------------------

    def test_04_parse_deposit_and_refund_lifecycle_events(self) -> None:
        blk = 12047890
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(101)
        tx_ref = _tx_hash(102)

        raw_logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [9900000000000000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x1",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [
                    _topic_Hash("RefundRequestCreated(uint256,address,uint256,string,uint256)"),
                    _topic_u256(0),
                    _topic_addr(STUDENT_A),
                ],
                "data": "0x" + abi_encode(["uint256", "string", "uint256"], [4000000000000000, "Overpaid", 1774000120]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x2",
                "logIndex": "0x1",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("RefundRequestReady(uint256)"), _topic_u256(0)],
                "data": "0x",
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x2",
                "logIndex": "0x2",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [
                    _topic_Hash("RefundRequestExecuted(uint256,address,uint256)"),
                    _topic_u256(0),
                    _topic_addr(STUDENT_A),
                ],
                "data": "0x" + abi_encode(["uint256"], [4000000000000000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x2",
                "logIndex": "0x3",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("RefundProcessed(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [4000000000000000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x2",
                "logIndex": "0x4",
            },
        ]

        res = self.indexer.ingest_raw_logs(raw_logs)
        self.assertEqual(res["totalUniqueIndexedLogs"], 5)
        names = [lg["eventName"] for lg in res["logs"]]
        self.assertEqual(
            names,
            [
                "FundDeposited",
                "RefundRequestCreated",
                "RefundRequestReady",
                "RefundRequestExecuted",
                "RefundProcessed",
            ],
        )
        self.assertEqual(res["logs"][1]["args"]["reason"], "Overpaid")
        self.assertEqual(res["logs"][3]["amountWei"], 4000000000000000)

    # ------------------------------------------------------------------------
    # Test 5: Block Timestamp Fetching & Block Header Caching
    # ------------------------------------------------------------------------

    def test_05_block_timestamp_fetching_and_header_caching(self) -> None:
        blk = 12047895
        b_hash = self.router.blocks[blk]["hash"]
        expected_ts = int(self.router.blocks[blk]["timestamp"], 16)

        # Three logs in the exact same block
        for idx in range(3):
            self.router.logs.append(
                {
                    "address": DEFAULT_CONTRACT_ADDRESS,
                    "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                    "data": "0x" + abi_encode(["uint256"], [1000 + idx]).hex(),
                    "blockNumber": hex(blk),
                    "blockHash": b_hash,
                    "transactionHash": _tx_hash(200 + idx),
                    "transactionIndex": hex(idx),
                    "logIndex": hex(idx),
                }
            )

        out = self.indexer.fetch_and_index_logs(blk, blk)
        self.assertEqual(out["newlyIndexedCount"], 3)
        for lg in out["logs"]:
            self.assertEqual(lg["blockTimestamp"], expected_ts)

        # Verify eth_getBlockByNumber was called ONLY ONCE for block 12047895
        self.assertEqual(self.router.get_block_calls_by_number.get(blk, 0), 1)

    # ------------------------------------------------------------------------
    # Test 6: Deduplication by `(chainId, transactionHash, logIndex)`
    # ------------------------------------------------------------------------

    def test_06_deduplication_by_composite_key_preserves_multi_event_tx(self) -> None:
        blk = 12047900
        b_hash = self.router.blocks[blk]["hash"]
        same_tx = _tx_hash(300)

        # In ProjectCore.deposit(), ONE transaction emits BOTH FundDeposited (logIndex 18)
        # AND AdminFeeCollected (logIndex 19).
        log_deposit = {
            "address": DEFAULT_CONTRACT_ADDRESS,
            "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
            "data": "0x" + abi_encode(["uint256"], [9900000000000000]).hex(),
            "blockNumber": hex(blk),
            "blockHash": b_hash,
            "transactionHash": same_tx,
            "transactionIndex": "0x6",
            "logIndex": "0x12",
        }
        log_fee = {
            "address": DEFAULT_CONTRACT_ADDRESS,
            "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
            "data": "0x" + abi_encode(["uint256"], [100000000000000]).hex(),
            "blockNumber": hex(blk),
            "blockHash": b_hash,
            "transactionHash": same_tx,
            "transactionIndex": "0x6",
            "logIndex": "0x13",
        }

        # Feed duplicate copies of both logs
        res = self.indexer.ingest_raw_logs([log_deposit, log_fee, log_deposit, log_fee])
        self.assertEqual(res["newlyIndexedCount"], 2)
        self.assertEqual(res["duplicatesSkipped"], 2)
        self.assertEqual(res["totalUniqueIndexedLogs"], 2)
        self.assertEqual(
            [lg["logKey"] for lg in res["logs"]],
            [
                build_composite_log_key(EXPECTED_SEPOLIA_CHAIN_ID, same_tx, 18),
                build_composite_log_key(EXPECTED_SEPOLIA_CHAIN_ID, same_tx, 19),
            ],
        )

    # ------------------------------------------------------------------------
    # Test 7, 8, 9: Campaign Classification by `blockTimestamp`
    # ------------------------------------------------------------------------

    def _get_migrated_campaigns(self) -> Dict[str, Dict[str, Any]]:
        raw_v1 = json.loads(REAL_ANNOUNCEMENTS_PATH.read_text(encoding="utf-8"))
        v2 = migrate_v1_to_v2_store(raw_v1)
        return v2["campaigns"]

    def test_07_classify_transaction_strictly_inside_campaign(self) -> None:
        campaigns = self._get_migrated_campaigns()
        # Campaign ann-k57-hk1: start=1792454400 (2026-10-20T00:00:00Z), end=1793619753
        # Pick timestamp well inside: 1793000000
        blk = 12047905
        self.router.blocks[blk]["timestamp"] = hex(1793000000)
        parsed = self.indexer.parse_raw_log(
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [9900000000000000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": self.router.blocks[blk]["hash"],
                "transactionHash": _tx_hash(701),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            }
        )
        classified = self.indexer.classify_deposit_log(parsed, campaigns)
        self.assertEqual(classified["classificationState"], "classified_by_block_timestamp")
        self.assertEqual(classified["allocatedCampaignId"], "ann-k57-hk1")
        self.assertFalse(classified["needsBoundaryReview"])

    def test_08_classify_transaction_near_boundary_or_shared_second_as_pending_reconciliation(self) -> None:
        campaigns = self._get_migrated_campaigns()
        # 1) Within +5s of startTimestamp (1792454400 + 5 = 1792454405 <= +12s safety window)
        blk1 = 12047906
        self.router.blocks[blk1]["timestamp"] = hex(1792454400 + 5)
        log1 = self.indexer.parse_raw_log(
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [9900000000000000]).hex(),
                "blockNumber": hex(blk1),
                "blockHash": self.router.blocks[blk1]["hash"],
                "transactionHash": _tx_hash(801),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            }
        )
        res1 = self.indexer.classify_deposit_log(log1, campaigns)
        self.assertEqual(res1["classificationState"], "pending_reconciliation")
        self.assertIsNone(res1["allocatedCampaignId"])
        self.assertTrue(res1["needsBoundaryReview"])

        # 2) At shared second 1793619753 between campaign ann-k57-hk1 and ann-20261102114233
        blk2 = 12047907
        self.router.blocks[blk2]["timestamp"] = hex(SHARED_SECOND_BOUNDARY_TS)
        log2 = self.indexer.parse_raw_log(
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_B)],
                "data": "0x" + abi_encode(["uint256"], [9900000000000000]).hex(),
                "blockNumber": hex(blk2),
                "blockHash": self.router.blocks[blk2]["hash"],
                "transactionHash": _tx_hash(802),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            }
        )
        res2 = self.indexer.classify_deposit_log(log2, campaigns)
        self.assertEqual(res2["classificationState"], "pending_reconciliation")
        self.assertIsNone(res2["allocatedCampaignId"])
        self.assertEqual(res2["candidateCampaignIds"], ["ann-k57-hk1", "ann-20261102114233"])

    def test_09_classify_transaction_outside_all_campaigns_as_unallocated(self) -> None:
        campaigns = self._get_migrated_campaigns()
        # Timestamp well before any campaign starts (1770000000)
        blk = 12047908
        self.router.blocks[blk]["timestamp"] = hex(1770000000)
        log_out = self.indexer.parse_raw_log(
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_C)],
                "data": "0x" + abi_encode(["uint256"], [5000000000000000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": self.router.blocks[blk]["hash"],
                "transactionHash": _tx_hash(901),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            }
        )
        res = self.indexer.classify_deposit_log(log_out, campaigns)
        self.assertEqual(res["classificationState"], "unallocated")
        self.assertIsNone(res["allocatedCampaignId"])
        self.assertEqual(res["assignedBucket"], "voluntaryContributions")

    # ------------------------------------------------------------------------
    # Test 10: Exact Integer Wei Preservation (No Float Precision Loss)
    # ------------------------------------------------------------------------

    def test_10_preserve_exact_wei_without_float_precision_loss(self) -> None:
        # 1.123456789012345679 ETH -> cannot be represented accurately in IEEE-754 float64!
        odd_wei = 1_123_456_789_012_345_679
        blk = 12047909
        parsed = self.indexer.parse_raw_log(
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [odd_wei]).hex(),
                "blockNumber": hex(blk),
                "blockHash": self.router.blocks[blk]["hash"],
                "transactionHash": _tx_hash(1001),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            }
        )
        self.assertIsInstance(parsed["amountWei"], int)
        self.assertEqual(parsed["amountWei"], odd_wei)
        self.assertEqual(parsed["amountWeiStr"], "1123456789012345679")
        self.assertEqual(parsed["amountEthDisplay"], "1.123456789012345679")
        self.assertEqual(wei_to_eth_display(1), "0.000000000000000001")

    # ------------------------------------------------------------------------
    # Test 11: Same-`blockTag` Smart Contract Reconciliation (3 Formulas + Fraud/Mismatch)
    # ------------------------------------------------------------------------

    def test_11_same_block_tag_contract_state_reconciliation_and_mismatch_detection(self) -> None:
        blk = 12047915
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]

        # Student A sent 10_000_000_000_000_000 wei (FundDeposited=10e15, AdminFeeCollected=100_000_000_000_000),
        # had 3_000_000_000_000_000 wei executed refund, and currently has a Pending refund (id=1) of 2_000_000_000_000_000 wei.
        # Student B sent 5_000_000_000_000_000 wei (FundDeposited=5e15, AdminFeeCollected=50_000_000_000_000)
        # and has a Ready refund (id=2) of 1_000_000_000_000_000 wei.
        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 2),
                "blockHash": self.router.blocks[blk - 2]["hash"],
                "transactionHash": _tx_hash(1101),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 2),
                "blockHash": self.router.blocks[blk - 2]["hash"],
                "transactionHash": _tx_hash(1101),
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [
                    _topic_Hash("RefundRequestExecuted(uint256,address,uint256)"),
                    _topic_u256(0),
                    _topic_addr(STUDENT_A),
                ],
                "data": "0x" + abi_encode(["uint256"], [3_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": _tx_hash(1102),
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("RefundProcessed(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [3_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": _tx_hash(1102),
                "transactionIndex": "0x0",
                "logIndex": "0x2",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_B)],
                "data": "0x" + abi_encode(["uint256"], [5_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": _tx_hash(1103),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_B)],
                "data": "0x" + abi_encode(["uint256"], [50_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": _tx_hash(1103),
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        self.router.state_by_block[b_tag] = {
            "classFundBalance": 11_850_000_000_000_000,  # 14.85e15 (classFundDeposits) - 3e15 (executed refund)
            "adminFeePool": 150_000_000_000_000,
            "reservedSpendAmount": 1_000_000_000_000_000,
            "reservedRefundAmount": 3_000_000_000_000_000,  # 2e15 (Pending) + 1e15 (Ready)
            "getAvailableClassFund": 7_850_000_000_000_000,  # 11.85e15 - 1e15 - 3e15
            "refundRequests": {
                0: {"applicant": STUDENT_A, "amount": 3_000_000_000_000_000, "status": REFUND_STATUS_EXECUTED},
                1: {"applicant": STUDENT_A, "amount": 2_000_000_000_000_000, "status": REFUND_STATUS_PENDING},
                2: {"applicant": STUDENT_B, "amount": 1_000_000_000_000_000, "status": REFUND_STATUS_READY},
            },
            "studentContributions": {
                STUDENT_A: 7_000_000_000_000_000,  # 10e15 - 3e15
                STUDENT_B: 5_000_000_000_000_000,
            },
            "pendingStudentRefundAmount": {
                STUDENT_A: 2_000_000_000_000_000,
                STUDENT_B: 1_000_000_000_000_000,
            },
            "getStudentAvailableContribution": {
                STUDENT_A: 5_000_000_000_000_000,  # 7e15 - 2e15
                STUDENT_B: 4_000_000_000_000_000,  # 5e15 - 1e15
            },
        }

        report = self.indexer.reconcile_contract_state_at_block(blk, [STUDENT_A, STUDENT_B])
        self.assertTrue(report["reconciled"])
        self.assertEqual(report["discrepancyCount"], 0)
        self.assertTrue(report["globalChecks"]["reservedRefundFormulaPassed"])
        self.assertTrue(report["globalChecks"]["availableClassFundFormulaPassed"])

        # Export snapshot to isolated temp file and verify safety guard
        temp_snapshot_path = self.temp_dir / "reconciliation_snapshot.json"
        written = self.indexer.export_snapshot_to_temp_file(report, temp_snapshot_path)
        self.assertTrue(Path(written).exists())
        with self.assertRaises(ReadOnlyPolicyViolationError):
            self.indexer.export_snapshot_to_temp_file(report, REAL_ANNOUNCEMENTS_PATH)

        # Now simulate a tampered/inconsistent state at block B (Fraud / State Divergence)
        self.router.state_by_block[b_tag]["reservedRefundAmount"] = 9_999_999
        bad_report = self.indexer.reconcile_contract_state_at_block(blk, [STUDENT_A, STUDENT_B])
        self.assertFalse(bad_report["reconciled"])
        self.assertGreaterEqual(bad_report["discrepancyCount"], 1)

    # ------------------------------------------------------------------------
    # Test 12: Simulated `blockHash` Change / `parentHash` Break (Reorg Detection)
    # ------------------------------------------------------------------------

    def test_12_detect_reorg_on_block_hash_change_and_flag_affected_logs(self) -> None:
        blk_a = 12047920
        blk_b = 12047921
        for b in (blk_a, blk_b):
            self.router.logs.append(
                {
                    "address": DEFAULT_CONTRACT_ADDRESS,
                    "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                    "data": "0x" + abi_encode(["uint256"], [1000]).hex(),
                    "blockNumber": hex(b),
                    "blockHash": self.router.blocks[b]["hash"],
                    "transactionHash": _tx_hash(1200 + b),
                    "transactionIndex": "0x0",
                    "logIndex": "0x0",
                }
            )

        self.indexer.fetch_and_index_logs(blk_a, blk_b)
        ref_headers = [self.indexer.get_block_header(blk_a), self.indexer.get_block_header(blk_b)]

        # Simulate a chain reorg at block blk_b where blockHash changes on RPC
        self.router.blocks[blk_b]["hash"] = _block_hash(blk_b, "f")

        reorg_res = self.indexer.detect_reorg_on_headers(ref_headers, refetch_from_rpc=True)
        self.assertTrue(reorg_res.reorg_detected)
        self.assertEqual(reorg_res.affected_from_block, blk_b)
        self.assertEqual(len(reorg_res.affected_log_keys), 1)

        # Verify the log at blk_b is marked needsReorgCheck=True, while blk_a remains False
        logs_by_blk = {lg["blockNumber"]: lg for lg in self.indexer._indexed_logs.values()}
        self.assertFalse(logs_by_blk[blk_a]["needsReorgCheck"])
        self.assertTrue(logs_by_blk[blk_b]["needsReorgCheck"])

    # ------------------------------------------------------------------------
    # Test 13: RPC Timeout and Retry with Backoff
    # ------------------------------------------------------------------------

    def test_13_rpc_timeout_and_retry_recovery(self) -> None:
        attempts = {"count": 0}
        sleep_calls: List[float] = []

        def flaky_transport(url: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise TimeoutError("Simulated Sepolia RPC timeout")
            return {"jsonrpc": "2.0", "id": payload["id"], "result": hex(EXPECTED_SEPOLIA_CHAIN_ID)}

        client = JsonRpcClient(
            rpc_url="https://flaky-sepolia.local",
            max_retries=3,
            retry_backoff_seconds=0.1,
            transport_fn=flaky_transport,
            sleep_fn=lambda s: sleep_calls.append(s),
        )
        res = client.call("eth_chainId", [])
        self.assertEqual(int(res, 16), EXPECTED_SEPOLIA_CHAIN_ID)
        self.assertEqual(attempts["count"], 3)
        self.assertEqual(sleep_calls, [0.1, 0.2])

        # Verify failure when all retries time out
        always_timeout_client = JsonRpcClient(
            rpc_url="https://down-sepolia.local",
            max_retries=2,
            retry_backoff_seconds=0.0,
            transport_fn=lambda u, p, t: (_ for _ in ()).throw(TimeoutError("Down")),
        )
        with self.assertRaises(RpcTransportError):
            always_timeout_client.call("eth_blockNumber", [])

    # ------------------------------------------------------------------------
    # Test 14: RPC Returning Invalid Data & Read-Only Security Guard (Fraud Prevention)
    # ------------------------------------------------------------------------

    def test_14_rpc_malformed_response_and_readonly_security_guard(self) -> None:
        # 1) Missing 'result' field
        bad_client_1 = JsonRpcClient(
            rpc_url="https://bad-sepolia.local",
            max_retries=1,
            transport_fn=lambda u, p, t: {"jsonrpc": "2.0", "id": 1},
        )
        with self.assertRaises(RpcTransportError):
            bad_client_1.call("eth_chainId", [])

        # 2) JSON-RPC error object returned
        bad_client_2 = JsonRpcClient(
            rpc_url="https://bad-sepolia.local",
            max_retries=1,
            transport_fn=lambda u, p, t: {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32005, "message": "limit exceeded"},
            },
        )
        with self.assertRaises(RpcTransportError):
            bad_client_2.call("eth_blockNumber", [])

        # 3) Fraud / Policy Violation: Attempt to call state-mutating eth_sendRawTransaction
        with self.assertRaises(ReadOnlyPolicyViolationError):
            self.rpc_client.call("eth_sendRawTransaction", ["0xdeadbeef"])

        # 4) Fraud / Policy Violation: Attempt to initialize indexer with a private key
        with self.assertRaises(ReadOnlyPolicyViolationError):
            BlockchainRPCIndexer(rpc_client=self.rpc_client, private_key="0x" + "1" * 64)

    # ========================================================================
    # PHASE 2.1 MANDATORY VERIFICATION & RECONCILIATION TESTS (TESTS 15 .. 23)
    # ========================================================================

    def test_15_p21_legacy_contract_gross_contribution_100_percent(self) -> None:
        """
        Phase 2.1 Test 1: Old/Legacy contract on Sepolia where deposit is 100% (10_000_000_000_000_000 wei),
        `FundDeposited` emits 99% (9_900_000_000_000_000 wei), `AdminFeeCollected` emits 1%
        (100_000_000_000_000 wei), and `studentContributions` increases by 100% (`msg.value`).
        Formula: `studentContributions = SUM(FundDeposited) + SUM(AdminFeeCollected) - SUM(RefundRequestExecuted)`.
        """
        blk = 12047923
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(1501)

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [9_900_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x6",
                "logIndex": "0x12",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x6",
                "logIndex": "0x13",
            },
        ]
        # Ingest duplicate copies to prove AdminFeeCollected is NEVER double-added
        self.indexer.ingest_raw_logs(logs + logs)

        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 9_900_000_000_000_000,
            "refundRequests": {},
            "studentContributions": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 10_000_000_000_000_000},
        }

        report = self.indexer.reconcile_contract_state_at_block(blk, [STUDENT_A])
        self.assertTrue(report["reconciled"])
        self.assertEqual(report["contractVersion"], CONTRACT_VERSION_LEGACY_GROSS)
        self.assertEqual(
            report["studentChecks"][STUDENT_A]["expectedStudentContributionsWei"],
            10_000_000_000_000_000,
        )
        self.assertEqual(
            report["studentChecks"][STUDENT_A]["sumAdminFeeCollectedWei"],
            100_000_000_000_000,
        )

    def test_16_p21_gross_contribution_contract_100_percent_event(self) -> None:
        """
        Phase 2.1/2.2.1 Test 2: Current ProjectCore.sol contract (`CONTRACT_VERSION_GROSS_CONTRIBUTION`)
        where `FundDeposited` emits 100% (`msg.value` = 10_000_000_000_000_000 wei),
        `AdminFeeCollected` emits 1% (100_000_000_000_000 wei), `studentContributions` increases
        by 100% (`msg.value`), and `classFundDeposits` is 99% (9_900_000_000_000_000 wei).
        Formula: `studentContributions = SUM(FundDeposited) - SUM(RefundRequestExecuted)`.
        """
        blk = 12047924
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(1601)

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x1",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x1",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 9_900_000_000_000_000,
            "refundRequests": {},
            "studentContributions": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 10_000_000_000_000_000},
        }

        report = self.indexer.reconcile_contract_state_at_block(blk, [STUDENT_A])
        self.assertTrue(report["reconciled"])
        self.assertEqual(report["contractVersion"], CONTRACT_VERSION_GROSS_CONTRIBUTION)
        self.assertEqual(
            report["studentChecks"][STUDENT_A]["expectedStudentContributionsWei"],
            10_000_000_000_000_000,
        )
        self.assertEqual(
            report["globalChecks"]["classFundDepositsWei"],
            9_900_000_000_000_000,
        )

    def test_17_p21_deposit_and_fee_events_in_different_transactions_detected(self) -> None:
        """
        Phase 2.1 Test 3: `FundDeposited` and `AdminFeeCollected` do NOT share the same `transactionHash`
        (or have mismatched student / wrong BPS ratio) -> must detect anomaly and fail reconciliation.
        """
        blk = 12047925
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [9_900_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": _tx_hash(1701),
                "transactionIndex": "0x1",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": _tx_hash(1702),  # Different transactionHash!
                "transactionIndex": "0x2",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 9_900_000_000_000_000,
            "refundRequests": {},
            "studentContributions": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 10_000_000_000_000_000},
        }

        report = self.indexer.reconcile_contract_state_at_block(blk, [STUDENT_A])
        self.assertFalse(report["reconciled"])
        self.assertFalse(report["eventPairingVerification"]["valid"])
        anomaly_types = [a["type"] for a in report["eventPairingVerification"]["anomalies"]]
        self.assertIn("MISSING_ADMIN_FEE_COLLECTED_EVENT", anomaly_types)
        self.assertIn("ORPHAN_ADMIN_FEE_COLLECTED_EVENT", anomaly_types)

    def test_18_p21_missing_admin_fee_collected_event_never_silently_ignored(self) -> None:
        """
        Phase 2.1 Test 4: `AdminFeeCollected` is missing from a deposit transaction ->
        must NOT be silently ignored; must flag `MISSING_ADMIN_FEE_COLLECTED_EVENT` and set `reconciled = False`.
        """
        blk = 12047926
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": _tx_hash(1801),
                "transactionIndex": "0x1",
                "logIndex": "0x0",
            }
        ]
        self.indexer.ingest_raw_logs(logs)

        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 9_900_000_000_000_000,
            "refundRequests": {},
            "studentContributions": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 10_000_000_000_000_000},
        }

        report = self.indexer.reconcile_contract_state_at_block(
            blk, [STUDENT_A], contract_version=CONTRACT_VERSION_GROSS_CONTRIBUTION
        )
        self.assertFalse(report["reconciled"])
        self.assertFalse(report["eventPairingVerification"]["valid"])
        self.assertEqual(
            report["eventPairingVerification"]["anomalies"][0]["type"],
            "MISSING_ADMIN_FEE_COLLECTED_EVENT",
        )

    def test_19_p21_refund_executed_and_processed_same_tx_subtracted_only_once(self) -> None:
        """
        Phase 2.1 Test 5: `RefundRequestExecuted` and `RefundProcessed` emitted in the same transaction ->
        only subtracted ONCE from `studentContributions` (both for legacy and new contract versions).
        """
        blk = 12047927
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(1901)
        tx_ref = _tx_hash(1902)

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [9_900_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [
                    _topic_Hash("RefundRequestExecuted(uint256,address,uint256)"),
                    _topic_u256(0),
                    _topic_addr(STUDENT_A),
                ],
                "data": "0x" + abi_encode(["uint256"], [4_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x1",
                "logIndex": "0x2",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("RefundProcessed(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [4_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x1",
                "logIndex": "0x3",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        # Legacy contract: 10e15 - 4e15 = 6e15 (if double-subtracted, it would be 2e15!)
        self.router.state_by_block[b_tag] = {
            "classFundBalance": 5_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 5_900_000_000_000_000,
            "refundRequests": {
                0: {"applicant": STUDENT_A, "amount": 4_000_000_000_000_000, "status": REFUND_STATUS_EXECUTED},
            },
            "studentContributions": {STUDENT_A: 6_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 6_000_000_000_000_000},
        }

        report = self.indexer.reconcile_contract_state_at_block(blk, [STUDENT_A])
        self.assertTrue(report["reconciled"])
        st_check = report["studentChecks"][STUDENT_A]
        self.assertEqual(st_check["sumRefundRequestExecutedWei"], 4_000_000_000_000_000)
        self.assertEqual(st_check["sumRefundProcessedWei"], 4_000_000_000_000_000)
        self.assertEqual(st_check["expectedStudentContributionsWei"], 6_000_000_000_000_000)
        self.assertTrue(st_check["dualRefundEventParityPassed"])

    def test_20_p21_deploy_block_distinct_from_first_observed_event_block(self) -> None:
        """
        Phase 2.1 Test 6: `deployBlock` (e.g. 12047880 with deployment transaction receipt) is
        distinct from `firstObservedEventBlock` (e.g. 12047881 where first BCSMemberUpdated log occurs)
        and `historyScanStartBlock`.
        """
        deploy_blk = 12047880
        first_event_blk = 12047881
        deploy_tx = _tx_hash(2000)
        self.router.seed_deployment_receipt(deploy_blk, deploy_tx)
        self.router.logs.append(
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("BCSMemberUpdated(address,bool)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["bool"], [True]).hex(),
                "blockNumber": hex(first_event_blk),
                "blockHash": self.router.blocks[first_event_blk]["hash"],
                "transactionHash": _tx_hash(2001),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            }
        )

        res = self.indexer.resolve_deploy_block(
            latest_block=12047930,
            search_floor_block=12047800,
            deployment_tx_hash=deploy_tx,
        )
        self.assertEqual(res["status"], DEPLOY_BLOCK_VERIFIED)
        self.assertEqual(res["deployBlock"], deploy_blk)
        self.assertEqual(res["firstObservedEventBlock"], first_event_blk)
        self.assertNotEqual(res["deployBlock"], res["firstObservedEventBlock"])
        self.assertEqual(res["historyScanStartBlock"], deploy_blk)
        self.assertEqual(res["deploymentTransactionHash"], deploy_tx)

    def test_21_p21_missing_deployment_transaction_returns_sync_config_required(self) -> None:
        """
        Phase 2.1 Test 7: When historical state is pruned on RPC and no deployment transaction receipt
        is available, `resolve_deploy_block()` MUST return `status = SYNC_CONFIG_REQUIRED` with
        `deployBlock = None`, MUST NOT treat `firstObservedEventBlock` (12047881) as `deployBlock`,
        and MUST NOT scan from genesis (block 0).
        """
        self.router.pruned_before_block = 12047925
        first_event_blk = 12047881
        self.router.logs.append(
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("BCSMemberUpdated(address,bool)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["bool"], [True]).hex(),
                "blockNumber": hex(first_event_blk),
                "blockHash": self.router.blocks[first_event_blk]["hash"],
                "transactionHash": _tx_hash(2101),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            }
        )

        res = self.indexer.resolve_deploy_block(
            latest_block=12047930,
            search_floor_block=12047800,
        )
        self.assertEqual(res["status"], SYNC_CONFIG_REQUIRED)
        self.assertIsNone(res["deployBlock"])
        self.assertEqual(res["firstObservedEventBlock"], first_event_blk)
        self.assertEqual(res["historyScanStartBlock"], 12047800)

        # Verify eth_getLogs was NEVER called from genesis (fromBlock = '0x0')
        for call_entry in self.rpc_client.call_history:
            if call_entry["method"] == "eth_getLogs":
                flt = call_entry["params"][0]
                self.assertGreater(int(flt["fromBlock"], 16), 0)

    def test_22_p21_unverified_abi_prevents_full_reconciliation_success(self) -> None:
        """
        Phase 2.1 Test 8: When `DEPLOYED_ABI_NOT_VERIFIED` is detected (either passed explicitly
        or when compiled runtime artifact differs from on-chain bytecode), reconciliation MUST NOT
        be marked as `reconciled = True` even if numbers match.
        """
        blk = 12047928
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(2201)

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [9_900_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 9_900_000_000_000_000,
            "refundRequests": {},
            "studentContributions": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 10_000_000_000_000_000},
        }

        # Case A: Explicit DEPLOYED_ABI_NOT_VERIFIED
        report_a = self.indexer.reconcile_contract_state_at_block(
            blk,
            [STUDENT_A],
            abi_verification_status=DEPLOYED_ABI_NOT_VERIFIED,
        )
        self.assertFalse(report_a["reconciled"])
        self.assertEqual(report_a["abiVerificationStatus"], DEPLOYED_ABI_NOT_VERIFIED)

        # Case B: Mismatched compiled runtime bytecode hex passed for strict verification
        report_b = self.indexer.reconcile_contract_state_at_block(
            blk,
            [STUDENT_A],
            compiled_runtime_bytecode_hex="0xdeadbeef1234",
        )
        self.assertFalse(report_b["reconciled"])
        self.assertEqual(report_b["abiVerificationStatus"], DEPLOYED_ABI_NOT_VERIFIED)

    def test_23_p21_two_contract_versions_never_misuse_each_others_formula(self) -> None:
        """
        Phase 2.1 Test 9: Verify that applying `CONTRACT_VERSION_GROSS_CONTRIBUTION` to a Legacy 99%-Event contract
        fails reconciliation, applying `CONTRACT_VERSION_LEGACY_GROSS` to a Gross Contribution 100%-Event contract
        fails reconciliation, and ambiguous state returns `CONTRACT_VERSION_UNVERIFIED`.
        """
        blk = 12047929
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(2301)

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [9_900_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        # 1) On-chain state is LEGACY_GROSS (10e15 with 9.9e15 event), but caller forces CONTRACT_VERSION_GROSS_CONTRIBUTION -> MUST FAIL
        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 9_900_000_000_000_000,
            "refundRequests": {},
            "studentContributions": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 10_000_000_000_000_000},
        }
        wrong_gross_on_legacy = self.indexer.reconcile_contract_state_at_block(
            blk, [STUDENT_A], contract_version=CONTRACT_VERSION_GROSS_CONTRIBUTION
        )
        self.assertFalse(wrong_gross_on_legacy["reconciled"])
        self.assertFalse(wrong_gross_on_legacy["studentChecks"][STUDENT_A]["formula1Passed"])

        # 2) Backward compatibility check: passing legacy string "NEW_NET_CONTRIBUTION" normalizes to GROSS_CONTRIBUTION
        self.assertEqual(
            normalize_contract_version("NEW_NET_CONTRIBUTION"),
            CONTRACT_VERSION_GROSS_CONTRIBUTION,
        )
        self.assertEqual(CONTRACT_VERSION_NEW_NET, CONTRACT_VERSION_GROSS_CONTRIBUTION)

        # 3) On-chain state matches neither (e.g. 8e15) and version is auto-detected -> CONTRACT_VERSION_UNVERIFIED
        self.router.state_by_block[b_tag]["studentContributions"][STUDENT_A] = 8_000_000_000_000_000
        self.router.state_by_block[b_tag]["getStudentAvailableContribution"][STUDENT_A] = 8_000_000_000_000_000
        unverified_res = self.indexer.reconcile_contract_state_at_block(blk, [STUDENT_A])
        self.assertFalse(unverified_res["reconciled"])
        self.assertEqual(unverified_res["contractVersion"], CONTRACT_VERSION_UNVERIFIED)

    # ========================================================================
    # PHASE 2.2.1 MANDATORY CONFIGURATION, ACCOUNTING & HISTORY SCAN TESTS
    # ========================================================================

    def test_24_p221_verified_deployment_config_and_env_override(self) -> None:
        """
        Phase 2.2.1 Section 2: Verify canonical deployment config (deployBlock=12042025,
        deployTxHash, contractCreator, contractAddress, chainId) and environment variable overrides.
        """
        default_cfg = load_deployment_config({})
        self.assertEqual(default_cfg.chain_id, 11155111)
        self.assertEqual(default_cfg.contract_address, "0x90948699FF04bC9cF159a39e200F09885439503D")
        self.assertEqual(default_cfg.contract_creator, "0x36Fd4887e9d1ecA4Ae5062A745cc2c6182B77060")
        self.assertEqual(
            default_cfg.deployment_tx_hash,
            "0x3b15cad8c8de4724cf31f9ec5212745a7f561749b0d3b74ebb6ed2371d2f2603",
        )
        self.assertEqual(default_cfg.deploy_block, 12042025)
        self.assertEqual(
            default_cfg.deploy_block_hash,
            "0x347c40a0578b588bc7729e6951c20b3788c041d48b508c1537c4816dbb81864e",
        )
        self.assertIsNone(default_cfg.history_scan_start_block)

        # Verify environment variable override works cleanly without hardcode duplication
        custom_env = {
            "CONTRACT_CHAIN_ID": "11155111",
            "CONTRACT_ADDRESS": "0x90948699ff04bc9cf159a39e200f09885439503d",
            "CONTRACT_CREATOR": "0x36fd4887e9d1eca4ae5062a745cc2c6182b77060",
            "CONTRACT_DEPLOY_TX_HASH": DEFAULT_DEPLOYMENT_TX_HASH.upper().replace("0X", "0x"),
            "CONTRACT_DEPLOY_BLOCK": "12042025",
            "HISTORY_SCAN_START_BLOCK": "12042100",
        }
        overridden_cfg = load_deployment_config(custom_env)
        self.assertEqual(overridden_cfg.deploy_block, 12042025)
        self.assertEqual(overridden_cfg.history_scan_start_block, 12042100)
        self.assertEqual(overridden_cfg.contract_creator, DEFAULT_CONTRACT_CREATOR)

        # Verify receipt validation against creator, contractAddress, and blockHash
        self.router.deploy_block = DEFAULT_DEPLOY_BLOCK
        self.router.blocks[DEFAULT_DEPLOY_BLOCK] = {
            "number": hex(DEFAULT_DEPLOY_BLOCK),
            "hash": DEFAULT_DEPLOY_BLOCK_HASH,
            "parentHash": _block_hash(DEFAULT_DEPLOY_BLOCK - 1),
            "timestamp": hex(1774000000),
            "transactions": [DEFAULT_DEPLOYMENT_TX_HASH],
        }
        self.router.receipts[DEFAULT_DEPLOYMENT_TX_HASH.lower()] = {
            "transactionHash": DEFAULT_DEPLOYMENT_TX_HASH,
            "blockNumber": hex(DEFAULT_DEPLOY_BLOCK),
            "blockHash": DEFAULT_DEPLOY_BLOCK_HASH,
            "from": DEFAULT_CONTRACT_CREATOR,
            "to": None,
            "contractAddress": DEFAULT_CONTRACT_ADDRESS,
            "status": "0x1",
        }
        prod_indexer = BlockchainRPCIndexer(rpc_client=self.rpc_client, config=default_cfg)
        resolved = prod_indexer.resolve_deploy_block(latest_block=12047930)
        self.assertEqual(resolved["status"], DEPLOY_BLOCK_VERIFIED)
        self.assertEqual(resolved["deployBlock"], 12042025)
        self.assertEqual(resolved["historyScanStartBlock"], 12042025)

    def test_25_p221_single_and_multiple_students_multiple_deposits_and_admin_fee_1_percent(self) -> None:
        """
        Phase 2.2.1 Section 4 Cases 1, 2, 8, 9:
        - Case 1: Single student depositing multiple times (Student A deposits 10e15 then 20e15).
        - Case 2: Multiple students depositing (Student A + Student B).
        - Case 8: Admin fee 1% (`FEE_BPS = 100 / 10000`).
        - Case 9: Class fund balance reconciliation:
          * `studentContributions[w] = SUM(FundDeposited[w]) - SUM(RefundRequestExecuted[w])`
          * `classFundDeposits = SUM(FundDeposited) - SUM(AdminFeeCollected)`
          * `AdminFeeCollected` is NEVER added to `studentContributions`
          * 1% fee is NEVER subtracted a second time from `classFundBalance`
        """
        blk = 12047930
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]

        # Student A Deposit #1: 10e15 wei (Fee: 0.1e15, Net: 9.9e15)
        # Student A Deposit #2: 20e15 wei (Fee: 0.2e15, Net: 19.8e15)
        # Student B Deposit #1: 50e15 wei (Fee: 0.5e15, Net: 49.5e15)
        deposits = [
            (STUDENT_A, 10_000_000_000_000_000, 100_000_000_000_000, _tx_hash(2501), 0),
            (STUDENT_A, 20_000_000_000_000_000, 200_000_000_000_000, _tx_hash(2502), 2),
            (STUDENT_B, 50_000_000_000_000_000, 500_000_000_000_000, _tx_hash(2503), 4),
        ]
        logs = []
        for student, gross_wei, fee_wei, tx_h, log_idx in deposits:
            logs.append(
                {
                    "address": DEFAULT_CONTRACT_ADDRESS,
                    "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(student)],
                    "data": "0x" + abi_encode(["uint256"], [gross_wei]).hex(),
                    "blockNumber": hex(blk),
                    "blockHash": b_hash,
                    "transactionHash": tx_h,
                    "transactionIndex": "0x0",
                    "logIndex": hex(log_idx),
                }
            )
            logs.append(
                {
                    "address": DEFAULT_CONTRACT_ADDRESS,
                    "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(student)],
                    "data": "0x" + abi_encode(["uint256"], [fee_wei]).hex(),
                    "blockNumber": hex(blk),
                    "blockHash": b_hash,
                    "transactionHash": tx_h,
                    "transactionIndex": "0x0",
                    "logIndex": hex(log_idx + 1),
                }
            )

        self.indexer.ingest_raw_logs(logs)

        # Total Gross FundDeposited = 80e15 wei
        # Total AdminFeeCollected (1%) = 0.8e15 wei
        # classFundDeposits (99%) = 79.2e15 wei
        self.router.state_by_block[b_tag] = {
            "classFundBalance": 79_200_000_000_000_000,
            "adminFeePool": 800_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 79_200_000_000_000_000,
            "refundRequests": {},
            "studentContributions": {
                STUDENT_A: 30_000_000_000_000_000,  # 10e15 + 20e15 (100% msg.value, NOT + 1% fee)
                STUDENT_B: 50_000_000_000_000_000,  # 50e15 (100% msg.value)
            },
            "pendingStudentRefundAmount": {STUDENT_A: 0, STUDENT_B: 0},
            "getStudentAvailableContribution": {
                STUDENT_A: 30_000_000_000_000_000,
                STUDENT_B: 50_000_000_000_000_000,
            },
        }

        report = self.indexer.reconcile_contract_state_at_block(
            blk, [STUDENT_A, STUDENT_B], contract_version=CONTRACT_VERSION_GROSS_CONTRIBUTION
        )
        self.assertTrue(report["reconciled"])
        self.assertEqual(report["contractVersion"], CONTRACT_VERSION_GROSS_CONTRIBUTION)
        self.assertEqual(
            report["studentChecks"][STUDENT_A]["expectedStudentContributionsWei"],
            30_000_000_000_000_000,
        )
        self.assertEqual(
            report["studentChecks"][STUDENT_B]["expectedStudentContributionsWei"],
            50_000_000_000_000_000,
        )
        self.assertEqual(report["globalChecks"]["sumFundDepositedWei"], 80_000_000_000_000_000)
        self.assertEqual(report["globalChecks"]["sumAdminFeeCollectedWei"], 800_000_000_000_000)
        self.assertEqual(report["globalChecks"]["classFundDepositsWei"], 79_200_000_000_000_000)
        self.assertTrue(report["globalChecks"]["classFundBalanceFormulaPassed"])
        self.assertTrue(report["globalChecks"]["adminFeePoolFormulaPassed"])

    def test_26_p221_multi_campaign_deposits_no_cross_campaign_misallocation(self) -> None:
        """
        Phase 2.2.1 Section 4 Case 3: Student depositing across multiple campaigns.
        Verify:
        - Deposits strictly inside Campaign 1 window map strictly to Campaign 1.
        - Deposits strictly inside Campaign 2 window map strictly to Campaign 2.
        - Deposits near campaign boundaries (`±12s`) go to `pending_reconciliation`
          and are NEVER misallocated to the wrong campaign.
        """
        blk_c1 = 12047890
        blk_boundary = 12047900
        blk_c2 = 12047910

        self.router.blocks[blk_c1]["timestamp"] = hex(1790001000)
        self.router.blocks[blk_boundary]["timestamp"] = hex(1790002000 + 5)  # 5s after C1 end -> pending_reconciliation
        self.router.blocks[blk_c2]["timestamp"] = hex(1790005000)

        campaigns = {
            "CAMPAIGN-K57-HK1": {
                "id": "CAMPAIGN-K57-HK1",
                "startTimestamp": 1790000000,
                "effectiveEndTimestamp": 1790002000,
                "deadlineTimestamp": 1790002000,
                "status": "closed",
            },
            "CAMPAIGN-K57-HK2": {
                "id": "CAMPAIGN-K57-HK2",
                "startTimestamp": 1790004000,
                "effectiveEndTimestamp": 1790006000,
                "deadlineTimestamp": 1790006000,
                "status": "active",
            },
        }

        raw_logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk_c1),
                "blockHash": self.router.blocks[blk_c1]["hash"],
                "transactionHash": _tx_hash(2601),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [15_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk_boundary),
                "blockHash": self.router.blocks[blk_boundary]["hash"],
                "transactionHash": _tx_hash(2602),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [25_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk_c2),
                "blockHash": self.router.blocks[blk_c2]["hash"],
                "transactionHash": _tx_hash(2603),
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
        ]

        ingest_res = self.indexer.ingest_raw_logs(raw_logs)
        self.assertEqual(ingest_res["newlyIndexedCount"], 3)

        summary = self.indexer.classify_all_indexed_deposits(campaigns=campaigns)
        self.assertTrue(summary["singleAssignmentInvariantPassed"])
        self.assertEqual(summary["countsByState"]["classified_by_block_timestamp"], 2)
        self.assertEqual(summary["countsByState"]["pending_reconciliation"], 1)

        by_tx = {item["transactionHash"]: item for item in summary["results"]}
        self.assertEqual(by_tx[_tx_hash(2601).lower()]["allocatedCampaignId"], "CAMPAIGN-K57-HK1")
        self.assertEqual(by_tx[_tx_hash(2601).lower()]["classificationState"], "classified_by_block_timestamp")

        self.assertIsNone(by_tx[_tx_hash(2602).lower()]["allocatedCampaignId"])
        self.assertEqual(by_tx[_tx_hash(2602).lower()]["classificationState"], "pending_reconciliation")

        self.assertEqual(by_tx[_tx_hash(2603).lower()]["allocatedCampaignId"], "CAMPAIGN-K57-HK2")
        self.assertEqual(by_tx[_tx_hash(2603).lower()]["classificationState"], "classified_by_block_timestamp")

    def test_27_p221_refund_executed_and_refund_processed_gross_contract_no_double_subtraction(self) -> None:
        """
        Phase 2.2.1 Section 4 Cases 4 & 5:
        - Case 4: `RefundRequestExecuted` subtracts from `studentContributions` and `classFundBalance`.
        - Case 5: `RefundProcessed` appearing in the same refund transaction is verified for 1:1 parity
          and NEVER double-subtracted under `CONTRACT_VERSION_GROSS_CONTRIBUTION`.
        """
        blk = 12047931
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(2701)
        tx_ref = _tx_hash(2702)

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [
                    _topic_Hash("RefundRequestExecuted(uint256,address,uint256)"),
                    _topic_u256(0),
                    _topic_addr(STUDENT_A),
                ],
                "data": "0x" + abi_encode(["uint256"], [3_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x1",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("RefundProcessed(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [3_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x1",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        # Gross contribution = 10e15 - 3e15 = 7e15
        # classFundDeposits = 10e15 - 0.1e15 = 9.9e15
        # classFundBalance = 9.9e15 - 3e15 = 6.9e15
        self.router.state_by_block[b_tag] = {
            "classFundBalance": 6_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 6_900_000_000_000_000,
            "refundRequests": {
                0: {"applicant": STUDENT_A, "amount": 3_000_000_000_000_000, "status": REFUND_STATUS_EXECUTED},
            },
            "studentContributions": {STUDENT_A: 7_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 7_000_000_000_000_000},
        }

        report = self.indexer.reconcile_contract_state_at_block(
            blk, [STUDENT_A], contract_version=CONTRACT_VERSION_GROSS_CONTRIBUTION
        )
        self.assertTrue(report["reconciled"])
        self.assertEqual(report["contractVersion"], CONTRACT_VERSION_GROSS_CONTRIBUTION)
        st = report["studentChecks"][STUDENT_A]
        self.assertEqual(st["expectedStudentContributionsWei"], 7_000_000_000_000_000)
        self.assertTrue(st["dualRefundEventParityPassed"])
        self.assertTrue(report["globalChecks"]["classFundBalanceFormulaPassed"])

    def test_28_p221_failed_refund_and_expired_refund_do_not_reduce_contributions_or_balance(self) -> None:
        """
        Phase 2.2.1 Section 4 Cases 6 & 7:
        - Case 6: Failed refund (`RefundExecutionFailed`) keeps request in `Ready` (status=1),
          keeps `reservedRefundAmount` & `pendingStudentRefundAmount` reserved, and does NOT
          reduce `studentContributions` or `classFundBalance`.
        - Case 7: Expired refund (`RefundRequestExpired(uint256)`) transitions request to `Expired` (status=4),
          releases `reservedRefundAmount` & `pendingStudentRefundAmount`, and does NOT reduce
          `studentContributions` or `classFundBalance`.
        """
        blk = 12047932
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(2801)
        tx_fail = _tx_hash(2802)
        tx_exp = _tx_hash(2803)

        logs = [
            # Student A deposits 10e15 wei (Fee 0.1e15, Net 9.9e15)
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
            # Refund #0 (2e15 wei) execution failed -> remains Ready (reserved)
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [
                    _topic_Hash("RefundExecutionFailed(uint256,address,uint256)"),
                    _topic_u256(0),
                    _topic_addr(STUDENT_A),
                ],
                "data": "0x" + abi_encode(["uint256"], [2_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_fail,
                "transactionIndex": "0x1",
                "logIndex": "0x0",
            },
            # Refund #1 (3e15 wei) expired -> RefundRequestExpired(uint256 indexed refundId)
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [
                    _topic_Hash("RefundRequestExpired(uint256)"),
                    _topic_u256(1),
                ],
                "data": "0x",
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_exp,
                "transactionIndex": "0x2",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,  # Unchanged by failed or expired refund
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 2_000_000_000_000_000,  # Only Refund #0 (Ready) is reserved; #1 (Expired) is released
            "getAvailableClassFund": 7_900_000_000_000_000,  # 9.9e15 - 2e15
            "refundRequests": {
                0: {"applicant": STUDENT_A, "amount": 2_000_000_000_000_000, "status": REFUND_STATUS_READY},
                1: {"applicant": STUDENT_A, "amount": 3_000_000_000_000_000, "status": REFUND_STATUS_EXPIRED},
            },
            "studentContributions": {STUDENT_A: 10_000_000_000_000_000},  # Unchanged!
            "pendingStudentRefundAmount": {STUDENT_A: 2_000_000_000_000_000},  # Only #0
            "getStudentAvailableContribution": {STUDENT_A: 8_000_000_000_000_000},  # 10e15 - 2e15
        }

        report = self.indexer.reconcile_contract_state_at_block(
            blk, [STUDENT_A], contract_version=CONTRACT_VERSION_GROSS_CONTRIBUTION
        )
        self.assertTrue(report["reconciled"])
        st = report["studentChecks"][STUDENT_A]
        self.assertEqual(st["sumRefundRequestExecutedWei"], 0)
        self.assertEqual(st["sumRefundExecutionFailedWei"], 2_000_000_000_000_000)
        self.assertEqual(st["expectedStudentContributionsWei"], 10_000_000_000_000_000)
        self.assertTrue(report["globalChecks"]["reservedRefundFormulaPassed"])

    def test_29_p221_adaptive_chunk_splitting_and_history_scan_completion_guard(self) -> None:
        """
        Phase 2.2.1 Section 4 Case 10 & Section 5:
        - Adaptive batch splitting when RPC rejects large block ranges (`max_blocks_per_query`),
          guaranteeing zero skipped blocks (`noBlocksSkipped = True`).
        - Deduplication by `chainId + txHash + logIndex`.
        - `scan_history_from_deploy_block` NEVER marks `syncCompleted = True` when any log is in
          `pending_reconciliation` or when a reorg is detected.
        """
        # Seed deployment receipt at block 12047880 so resolve_deploy_block verifies 12047880
        deploy_blk = 12047880
        deploy_tx = _tx_hash(2900)
        self.router.seed_deployment_receipt(deploy_blk, deploy_tx)
        self.indexer.deployment_tx_hash = deploy_tx

        # Configure router to reject eth_getLogs spanning more than 7 blocks
        self.router.max_blocks_per_query = 7

        blk_1 = 12047885
        blk_1_ts = int(self.router.blocks[blk_1]["timestamp"], 16)
        tx_dep = _tx_hash(2901)

        raw_logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk_1),
                "blockHash": self.router.blocks[blk_1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk_1),
                "blockHash": self.router.blocks[blk_1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
        ]
        # Push duplicate logs into RPC router to verify deduplication during scan
        self.router.logs.extend(raw_logs + raw_logs)

        end_blk = 12047910
        b_tag = hex(end_blk)
        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 9_900_000_000_000_000,
            "refundRequests": {},
            "studentContributions": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 10_000_000_000_000_000},
        }

        # 1) Scan with a campaign whose boundary is 3s away from blk_1 -> deposit goes to pending_reconciliation -> syncCompleted MUST be False!
        boundary_campaign = {
            "CAMPAIGN-BOUNDARY": {
                "id": "CAMPAIGN-BOUNDARY",
                "startTimestamp": blk_1_ts - 3,  # Within 12s boundary safety window!
                "effectiveEndTimestamp": blk_1_ts + 5000,
                "deadlineTimestamp": blk_1_ts + 5000,
                "status": "active",
            }
        }
        scan_pending = self.indexer.scan_history_from_deploy_block(
            to_block=end_blk,
            from_block=deploy_blk,
            campaigns=boundary_campaign,
            batch_size=20,  # Larger than router limit (7) -> triggers adaptive halving!
            student_wallets=[STUDENT_A],
            contract_version=CONTRACT_VERSION_GROSS_CONTRIBUTION,
        )
        self.assertTrue(scan_pending["noBlocksSkipped"])
        self.assertGreater(scan_pending["chunkCount"], 2)
        self.assertEqual(scan_pending["inserted"], 2)
        self.assertEqual(scan_pending["duplicatesSkipped"], 2)
        self.assertEqual(scan_pending["pendingReconciliationCount"], 1)
        self.assertFalse(scan_pending["syncCompleted"])
        self.assertEqual(scan_pending["syncStatus"], "PENDING_RECONCILIATION")

        # 2) Scan WITH strictly enclosing campaign window -> 0 pending_reconciliation -> syncCompleted = True!
        indexer_clean = BlockchainRPCIndexer(
            rpc_client=self.rpc_client,
            deploy_block=deploy_blk,
            deployment_tx_hash=deploy_tx,
            max_block_range=20,
        )
        valid_campaign = {
            "CAMPAIGN-FULL": {
                "id": "CAMPAIGN-FULL",
                "startTimestamp": blk_1_ts - 1000,
                "effectiveEndTimestamp": blk_1_ts + 10000,
                "deadlineTimestamp": blk_1_ts + 10000,
                "status": "active",
            }
        }
        scan_ok = indexer_clean.scan_history_from_deploy_block(
            to_block=end_blk,
            from_block=deploy_blk,
            campaigns=valid_campaign,
            batch_size=20,
            student_wallets=[STUDENT_A],
            contract_version=CONTRACT_VERSION_GROSS_CONTRIBUTION,
        )
        self.assertTrue(scan_ok["noBlocksSkipped"])
        self.assertEqual(scan_ok["pendingReconciliationCount"], 0)
        self.assertTrue(scan_ok["reconciled"])
        self.assertTrue(scan_ok["syncCompleted"])
        self.assertEqual(scan_ok["syncStatus"], "SYNC_COMPLETED")

    # ========================================================================
    # LAB 15 PHASE 1 – NET_CONTRIBUTION RECONCILIATION TESTS
    # ========================================================================

    def test_30_phase1_net_contribution_auto_detect_and_full_refund(self) -> None:
        """
        Phase 1: Upgraded `ProjectCore.sol` stores 99% net in `studentContributions`,
        100% gross in `studentTotalDeposited`, and exposes `getStudentMaxRefund`.
        Even after full 99% net refund (`studentContributions == 0`), auto-detection
        identifies `CONTRACT_VERSION_NET_CONTRIBUTION` and reconciles cleanly.
        """
        blk = 12047940
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(3001)
        tx_ref = _tx_hash(3002)

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk - 1),
                "blockHash": self.router.blocks[blk - 1]["hash"],
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [
                    _topic_Hash("RefundRequestExecuted(uint256,address,uint256)"),
                    _topic_u256(1),
                    _topic_addr(STUDENT_A),
                ],
                "data": "0x" + abi_encode(["uint256"], [9_900_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x1",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("RefundProcessed(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [9_900_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_ref,
                "transactionIndex": "0x1",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        self.router.state_by_block[b_tag] = {
            "classFundBalance": 0,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 0,
            "refundRequests": {
                0: {"applicant": STUDENT_A, "amount": 9_900_000_000_000_000, "status": REFUND_STATUS_EXECUTED},
            },
            "studentContributions": {STUDENT_A: 0},
            "studentTotalDeposited": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 0},
            "getStudentMaxRefund": {STUDENT_A: 0},
        }

        self.assertEqual(normalize_contract_version("NET_CONTRIBUTION"), CONTRACT_VERSION_NET_CONTRIBUTION)
        report = self.indexer.reconcile_contract_state_at_block(blk, [STUDENT_A], contract_version=None)
        self.assertTrue(report["reconciled"])
        self.assertEqual(report["contractVersion"], CONTRACT_VERSION_NET_CONTRIBUTION)
        st = report["studentChecks"][STUDENT_A]
        self.assertTrue(st["formula1Passed"])
        self.assertTrue(st["totalDepositedFormulaPassed"])
        self.assertTrue(st["maxRefundFormulaPassed"])
        self.assertEqual(st["expectedStudentContributionsWei"], 0)
        self.assertEqual(st["expectedStudentTotalDepositedWei"], 10_000_000_000_000_000)

    def test_31_phase1_net_contribution_rejects_gross_state_and_tampered_views(self) -> None:
        """
        Phase 1 negative/fraud tests:
        - Applying `NET_CONTRIBUTION` to a gross contract (`studentContributions == 10e15`) fails.
        - Tampering `studentTotalDeposited` or `getStudentMaxRefund` is detected as a discrepancy.
        """
        blk = 12047938
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(3101)

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        # Case A: Gross value on NET_CONTRIBUTION must fail
        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 0,
            "reservedRefundAmount": 0,
            "getAvailableClassFund": 9_900_000_000_000_000,
            "refundRequests": {},
            "studentContributions": {STUDENT_A: 10_000_000_000_000_000},
            "studentTotalDeposited": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 0},
            "getStudentAvailableContribution": {STUDENT_A: 10_000_000_000_000_000},
            "getStudentMaxRefund": {STUDENT_A: 9_900_000_000_000_000},
        }
        gross_fail = self.indexer.reconcile_contract_state_at_block(
            blk, [STUDENT_A], contract_version=CONTRACT_VERSION_NET_CONTRIBUTION
        )
        self.assertFalse(gross_fail["reconciled"])
        self.assertFalse(gross_fail["studentChecks"][STUDENT_A]["formula1Passed"])

        # Case B: Net studentContributions matches, but studentTotalDeposited & getStudentMaxRefund tampered
        self.router.state_by_block[b_tag].update(
            {
                "studentContributions": {STUDENT_A: 9_900_000_000_000_000},
                "studentTotalDeposited": {STUDENT_A: 9_900_000_000_000_000},  # tampered!
                "getStudentAvailableContribution": {STUDENT_A: 9_900_000_000_000_000},
                "getStudentMaxRefund": {STUDENT_A: 10_000_000_000_000_000},  # tampered!
            }
        )
        tamper_fail = self.indexer.reconcile_contract_state_at_block(
            blk, [STUDENT_A], contract_version=CONTRACT_VERSION_NET_CONTRIBUTION
        )
        self.assertFalse(tamper_fail["reconciled"])
        self.assertFalse(tamper_fail["studentChecks"][STUDENT_A]["totalDepositedFormulaPassed"])
        self.assertFalse(tamper_fail["studentChecks"][STUDENT_A]["maxRefundFormulaPassed"])

    def test_32_phase1_net_contribution_with_pending_refund_and_spend_reserve(self) -> None:
        """
        Phase 1: Verify `getStudentMaxRefund == min(getStudentAvailableContribution, getAvailableClassFund)`
        when pending refunds and reserved spend amounts both exist.
        """
        blk = 12047939
        b_tag = hex(blk)
        b_hash = self.router.blocks[blk]["hash"]
        tx_dep = _tx_hash(3201)

        logs = [
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("FundDeposited(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [10_000_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x0",
            },
            {
                "address": DEFAULT_CONTRACT_ADDRESS,
                "topics": [_topic_Hash("AdminFeeCollected(address,uint256)"), _topic_addr(STUDENT_A)],
                "data": "0x" + abi_encode(["uint256"], [100_000_000_000_000]).hex(),
                "blockNumber": hex(blk),
                "blockHash": b_hash,
                "transactionHash": tx_dep,
                "transactionIndex": "0x0",
                "logIndex": "0x1",
            },
        ]
        self.indexer.ingest_raw_logs(logs)

        self.router.state_by_block[b_tag] = {
            "classFundBalance": 9_900_000_000_000_000,
            "adminFeePool": 100_000_000_000_000,
            "reservedSpendAmount": 4_000_000_000_000_000,
            "reservedRefundAmount": 2_000_000_000_000_000,
            "getAvailableClassFund": 3_900_000_000_000_000,  # 9.9e15 - 4e15 - 2e15
            "refundRequests": {
                0: {"applicant": STUDENT_A, "amount": 2_000_000_000_000_000, "status": REFUND_STATUS_PENDING},
            },
            "studentContributions": {STUDENT_A: 9_900_000_000_000_000},
            "studentTotalDeposited": {STUDENT_A: 10_000_000_000_000_000},
            "pendingStudentRefundAmount": {STUDENT_A: 2_000_000_000_000_000},
            "getStudentAvailableContribution": {STUDENT_A: 7_900_000_000_000_000},
            "getStudentMaxRefund": {STUDENT_A: 3_900_000_000_000_000},  # min(7.9e15, 3.9e15)
        }

        report = self.indexer.reconcile_contract_state_at_block(
            blk, [STUDENT_A], contract_version=CONTRACT_VERSION_NET_CONTRIBUTION
        )
        self.assertTrue(report["reconciled"])
        st = report["studentChecks"][STUDENT_A]
        self.assertEqual(st["expectedStudentMaxRefundWei"], 3_900_000_000_000_000)
        self.assertTrue(st["maxRefundFormulaPassed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
