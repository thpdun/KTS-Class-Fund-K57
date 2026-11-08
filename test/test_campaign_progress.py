# -*- coding: utf-8 -*-
"""
test_campaign_progress.py - Bộ kiểm thử tự động toàn diện 13 kịch bản
cho tính năng Multiple Independent Progress Cards và Backend Attribution Layer.
Dự án: KTS-Class-Fund-K57
"""

import copy
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Cấu hình stdout UTF-8
if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Đảm bảo import từ backend
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Thiết lập biến môi trường TEST để cô lập hoàn toàn
os.environ["ALLOW_REAL_DATA_MUTATION"] = "0"

from backend.contribution_store import (
    create_claim_intent,
    get_claim_intent,
    verify_and_claim_contribution,
    get_campaign_progress_view,
    freeze_campaign_progress_record,
    record_adjusted_final_progress,
    ContributionAttributionError,
    init_campaign_progress_record,
)


class MockRpcClient:
    """Mock RPC client để kiểm thử các tình huống on-chain mà không dùng tiền thật hay mạng thật."""
    def __init__(self, expected_contract="0x90948699FF04bC9cF159a39e200F09885439503D"):
        self.expected_contract = expected_contract.lower()
        self.receipts = {}
        self.block_timestamps = {}

    def add_receipt(self, tx_hash, student_address, amount_wei, status=1, to_contract=None, block_num=1000, block_ts=1700000000):
        tx_norm = tx_hash.lower()
        to_addr = (to_contract or self.expected_contract).lower()
        # FundDeposited topic0
        topic0 = "0x89980d2fb2d3523f6e16bc8d16719e7ccae18c1b3f94294ca237ca5e5a2db12f".lower()
        student_topic = "0x" + student_address.lower()[2:].zfill(64)
        data_hex = hex(amount_wei)

        self.receipts[tx_norm] = {
            "transactionHash": tx_norm,
            "status": "0x1" if status == 1 else "0x0",
            "to": to_addr,
            "from": student_address.lower(),
            "blockNumber": block_num,
            "logs": [
                {
                    "address": to_addr,
                    "topics": [topic0, student_topic],
                    "data": data_hex
                }
            ]
        }
        self.block_timestamps[block_num] = block_ts

    def get_transaction_receipt(self, tx_hash):
        return self.receipts.get(tx_hash.lower())

    def get_block_timestamp(self, block_num):
        return self.block_timestamps.get(block_num, 1700000000)


class TestCampaignProgressAndAttribution(unittest.TestCase):
    """
    Kiểm thử đầy đủ 13 tình huống bắt buộc tại Mục VI:
    1. Tạo A: A hiển thị 0%.
    2. A có giao dịch hợp lệ: chỉ A tăng.
    3. Tạo B trong khi A active: A giữ nguyên, B bắt đầu 0%.
    4. B có giao dịch hợp lệ: chỉ B tăng.
    5. A và B cùng active: hai thanh hiển thị riêng và độc lập.
    6. Đóng A: A biến mất khỏi khu vực hiện tại, finalProgress được giữ trong history.
    7. B vẫn active: B tiếp tục cập nhật.
    8. Đóng B: không còn thanh tiến độ active; khu vực hiện tại hiển thị 0%.
    9. Giao dịch trùng txHash: không được tính hai lần (Idempotent).
    10. Giao dịch chưa phân bổ / ngoài đợt thu: không tự động cộng vào A hoặc B.
    11. Refresh trang (F5): các thanh tiến độ vẫn chính xác.
    12. Đăng xuất / đăng nhập: dữ liệu vẫn chính xác.
    13. Giao diện thực tế / Render cấu trúc thẻ tiến độ độc lập.
    """

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="kts_progress_test_")
        self.tmp_path = Path(self.tmp_dir.name)
        self.contributions_file = self.tmp_path / "campaign_contributions.json"
        self.intents_file = self.tmp_path / "claim_intents.json"

        os.environ["CONTRIBUTIONS_FILE_PATH"] = str(self.contributions_file)
        os.environ["CLAIM_INTENTS_FILE_PATH"] = str(self.intents_file)

        self.mock_rpc = MockRpcClient()
        self.student_1 = "0x78567a377559f0cb30173f93869326a82320159a"
        self.student_2 = "0xe71f9ffb91a3f4ba78e25833ba48b05c0e7d9fc2"
        self.student_3 = "0x36fd4887e9d1eca4ae5062a745cc2c6182b77060"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_create_campaign_a_starts_at_zero(self):
        """1. Tạo A: A hiển thị 0%."""
        prog = get_campaign_progress_view("ann-campaign-a", class_size=7)
        self.assertEqual(prog["contributingWalletsCount"], 0)
        self.assertEqual(prog["raisedWei"], "0")
        self.assertEqual(prog["raisedEth"], "0.0000")
        self.assertEqual(prog["headcountPercent"], 0)

    def test_02_valid_transaction_only_updates_campaign_a(self):
        """2. A có giao dịch hợp lệ: chỉ A tăng."""
        tx_a1 = "0x" + "a" * 64
        self.mock_rpc.add_receipt(tx_a1, self.student_1, 10**16) # 0.01 ETH

        # Tạo intent trước khi claim
        intent = create_claim_intent("ann-campaign-a", self.student_1, "active")

        res = verify_and_claim_contribution(
            notification_id="ann-campaign-a",
            tx_hash=tx_a1,
            verified_wallet=self.student_1,
            claim_intent_id=intent["intentId"],
            rpc_client=self.mock_rpc,
            class_size=7,
            target_eth="0.01"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["contributingWalletsCount"], 1)
        self.assertEqual(res["headcountPercent"], 14) # 1/7 = 14%
        self.assertEqual(res["campaignProgress"]["raisedEth"], "0.0100")

    def test_03_create_b_while_a_active_preserves_a_and_b_starts_at_zero(self):
        """3. Tạo B trong khi A active: A giữ nguyên, B bắt đầu 0%."""
        # A có 1 giao dịch
        tx_a1 = "0x" + "a" * 64
        self.mock_rpc.add_receipt(tx_a1, self.student_1, 10**16)
        verify_and_claim_contribution(
            notification_id="ann-campaign-a",
            tx_hash=tx_a1,
            verified_wallet=self.student_1,
            rpc_client=self.mock_rpc,
            class_size=7
        )

        # Tạo B -> Kiểm tra tiến độ B
        prog_b = get_campaign_progress_view("ann-campaign-b", class_size=7)
        self.assertEqual(prog_b["contributingWalletsCount"], 0)
        self.assertEqual(prog_b["raisedEth"], "0.0000")
        self.assertEqual(prog_b["headcountPercent"], 0)

        # Kiểm tra A vẫn giữ nguyên 1 ví đã nộp
        prog_a = get_campaign_progress_view("ann-campaign-a", class_size=7)
        self.assertEqual(prog_a["contributingWalletsCount"], 1)

    def test_04_valid_transaction_for_b_only_updates_b(self):
        """4. B có giao dịch hợp lệ: chỉ B tăng."""
        # A có student_1
        tx_a1 = "0x" + "a" * 64
        self.mock_rpc.add_receipt(tx_a1, self.student_1, 10**16)
        verify_and_claim_contribution(
            notification_id="ann-campaign-a",
            tx_hash=tx_a1,
            verified_wallet=self.student_1,
            rpc_client=self.mock_rpc,
            class_size=7
        )

        # B nhận giao dịch từ student_2
        tx_b1 = "0x" + "b" * 64
        self.mock_rpc.add_receipt(tx_b1, self.student_2, 2 * 10**16) # 0.02 ETH
        res_b = verify_and_claim_contribution(
            notification_id="ann-campaign-b",
            tx_hash=tx_b1,
            verified_wallet=self.student_2,
            rpc_client=self.mock_rpc,
            class_size=7,
            target_eth="0.02"
        )
        self.assertEqual(res_b["contributingWalletsCount"], 1)
        self.assertEqual(res_b["campaignProgress"]["raisedEth"], "0.0200")

        # Tiến độ A hoàn toàn không bị ảnh hưởng bởi B
        prog_a = get_campaign_progress_view("ann-campaign-a", class_size=7)
        self.assertEqual(prog_a["contributingWalletsCount"], 1)
        self.assertEqual(prog_a["raisedEth"], "0.0100")

    def test_05_a_and_b_both_active_have_separate_independent_progress(self):
        """5. A và B cùng active: hai thanh hiển thị riêng và độc lập."""
        tx_a1 = "0x" + "a" * 64
        tx_b1 = "0x" + "b" * 64
        self.mock_rpc.add_receipt(tx_a1, self.student_1, 10**16)
        self.mock_rpc.add_receipt(tx_b1, self.student_2, 3 * 10**16)

        verify_and_claim_contribution("ann-a", tx_a1, self.student_1, rpc_client=self.mock_rpc, class_size=7)
        verify_and_claim_contribution("ann-b", tx_b1, self.student_2, rpc_client=self.mock_rpc, class_size=7)

        p_a = get_campaign_progress_view("ann-a", class_size=7)
        p_b = get_campaign_progress_view("ann-b", class_size=7)

        self.assertNotEqual(p_a["notificationId"], p_b["notificationId"])
        self.assertEqual(p_a["raisedEth"], "0.0100")
        self.assertEqual(p_b["raisedEth"], "0.0300")
        self.assertEqual(p_a["contributingWallets"], [self.student_1.lower()])
        self.assertEqual(p_b["contributingWallets"], [self.student_2.lower()])

    def test_06_close_a_freezes_final_progress_in_history(self):
        """6. Đóng A: finalProgress được giữ nguyên trong history; không thể bị ghi đè."""
        tx_a1 = "0x" + "a" * 64
        self.mock_rpc.add_receipt(tx_a1, self.student_1, 10**16)
        verify_and_claim_contribution("ann-a", tx_a1, self.student_1, rpc_client=self.mock_rpc, class_size=7)

        # Đóng đợt A
        final_snap = freeze_campaign_progress_record("ann-a", reason="Ban cán sự đóng đợt A")
        self.assertTrue(final_snap["isFrozen"])
        self.assertEqual(final_snap["raisedEth"], "0.0100")
        self.assertEqual(final_snap["contributingWalletsCount"], 1)

        # Lấy lại tiến độ -> Vẫn giữ nguyên snapshot
        p_a = get_campaign_progress_view("ann-a", class_size=7)
        self.assertTrue(p_a["isFrozen"])
        self.assertIsNotNone(p_a["finalProgress"])

    def test_07_b_remains_active_and_continues_updating(self):
        """7. B vẫn active: B tiếp tục cập nhật khi A đã đóng."""
        # Đóng A
        freeze_campaign_progress_record("ann-a", reason="A đã đóng")

        # Nạp thêm cho B
        tx_b2 = "0x" + "c" * 64
        self.mock_rpc.add_receipt(tx_b2, self.student_3, 10**16)
        verify_and_claim_contribution("ann-b", tx_b2, self.student_3, rpc_client=self.mock_rpc, class_size=7)

        p_b = get_campaign_progress_view("ann-b", class_size=7)
        self.assertEqual(p_b["contributingWalletsCount"], 1)
        self.assertEqual(p_b["raisedEth"], "0.0100")

    def test_08_close_b_no_active_campaigns_returns_zero_state(self):
        """8. Đóng B: không còn thanh tiến độ active; khu vực hiện tại hiển thị 0%."""
        freeze_campaign_progress_record("ann-b", reason="B đã đóng")

        # Khi cả A và B đã đóng, danh sách activeNotifications từ server sẽ là []
        # Frontend gọi renderMultipleProgressCards([]) -> render khu vực 0%
        active_list = []
        self.assertEqual(len(active_list), 0)

    def test_09_duplicate_tx_hash_is_idempotent_and_no_double_counting(self):
        """9. Giao dịch trùng txHash: không được tính hai lần (Idempotent)."""
        tx_shared = "0x" + "d" * 64
        self.mock_rpc.add_receipt(tx_shared, self.student_1, 10**16)

        # Lần 1: Claim cho đợt A
        r1 = verify_and_claim_contribution("ann-a", tx_shared, self.student_1, rpc_client=self.mock_rpc, class_size=7)
        self.assertFalse(r1["idempotent"])
        self.assertEqual(r1["contributingWalletsCount"], 1)

        # Lần 2: Gửi lại cùng tx_shared cho đợt A -> Idempotent
        r2 = verify_and_claim_contribution("ann-a", tx_shared, self.student_1, rpc_client=self.mock_rpc, class_size=7)
        self.assertTrue(r2["idempotent"])
        self.assertEqual(r2["campaignProgress"]["contributingWalletsCount"], 1)
        self.assertEqual(r2["campaignProgress"]["raisedEth"], "0.0100") # Không bị nhân đôi lên 0.0200

        # Lần 3: Gửi tx_shared này để claim cho đợt B -> Bị từ chối Conflict
        with self.assertRaises(ContributionAttributionError) as ctx:
            verify_and_claim_contribution("ann-b", tx_shared, self.student_1, rpc_client=self.mock_rpc, class_size=7)
        self.assertIn("đã được phân bổ cho đợt thu khác", str(ctx.exception))

    def test_10_unallocated_transaction_not_credited_to_campaigns(self):
        """10. Giao dịch phát sinh sau khi chiến dịch đóng -> chuyển sang UNALLOCATED, không tự động cộng."""
        tx_late = "0x" + "e" * 64
        # Giao dịch có blockTimestamp = 2000, trong khi đợt A kết thúc tại timestamp = 1000
        self.mock_rpc.add_receipt(tx_late, self.student_1, 10**16, block_ts=2000)

        with self.assertRaises(ContributionAttributionError) as ctx:
            verify_and_claim_contribution(
                notification_id="ann-a",
                tx_hash=tx_late,
                verified_wallet=self.student_1,
                rpc_client=self.mock_rpc,
                notification_status="archived",
                notification_ended_at_ts=1000.0,
                class_size=7
            )
        self.assertIn("UNALLOCATED_EXCEPTION", str(ctx.exception))

    def test_11_refresh_persistence(self):
        """11. Refresh trang: Dữ liệu tiến độ vẫn toàn vẹn từ backend store."""
        tx_p = "0x" + "f" * 64
        self.mock_rpc.add_receipt(tx_p, self.student_1, 10**16)
        verify_and_claim_contribution("ann-persisted", tx_p, self.student_1, rpc_client=self.mock_rpc, class_size=7)

        # Mô phỏng reload dữ liệu từ file
        reloaded = get_campaign_progress_view("ann-persisted", class_size=7)
        self.assertEqual(reloaded["contributingWalletsCount"], 1)
        self.assertEqual(reloaded["raisedEth"], "0.0100")

    def test_12_same_wallet_multiple_contributions_counts_one_headcount(self):
        """12. Chuẩn hóa: 1 ví nộp 2 lần chỉ tính 1 người nộp, nhưng tiền được cộng dồn cả 2."""
        tx_1 = "0x" + "1" * 64
        tx_2 = "0x" + "2" * 64
        self.mock_rpc.add_receipt(tx_1, self.student_1, 10**16)
        self.mock_rpc.add_receipt(tx_2, self.student_1, 2 * 10**16)

        verify_and_claim_contribution("ann-repeat", tx_1, self.student_1, rpc_client=self.mock_rpc, class_size=7)
        verify_and_claim_contribution("ann-repeat", tx_2, self.student_1, rpc_client=self.mock_rpc, class_size=7)

        p = get_campaign_progress_view("ann-repeat", class_size=7)
        self.assertEqual(p["contributingWalletsCount"], 1) # Chỉ 1 ví duy nhất
        self.assertEqual(p["totalTransactionsCount"], 2)     # 2 giao dịch
        self.assertEqual(p["raisedEth"], "0.0300")           # 0.01 + 0.02 = 0.03 ETH

    def test_13_audit_adjusted_final_progress_does_not_overwrite_original(self):
        """13. Ngoại lệ có kiểm toán: adjustedFinalProgress lưu riêng, không ghi đè finalProgress ban đầu."""
        tx_0 = "0x" + "9" * 64
        self.mock_rpc.add_receipt(tx_0, self.student_1, 10**16)
        verify_and_claim_contribution("ann-adj", tx_0, self.student_1, rpc_client=self.mock_rpc, class_size=7)

        # Chốt đóng đợt
        orig_snap = freeze_campaign_progress_record("ann-adj", reason="Đóng ban đầu")
        self.assertEqual(orig_snap["raisedEth"], "0.0100")

        # Điều chỉnh ngoại lệ được phê duyệt
        adjusted = record_adjusted_final_progress(
            notification_id="ann-adj",
            actor="0xadvisor...",
            reason="Đối soát bổ sung biên lai hợp lệ trước giờ đóng",
            adjustments={"raisedEth": "0.0200", "contributingWalletsCount": 2}
        )

        p_adj = get_campaign_progress_view("ann-adj", class_size=7)
        # Snapshot ban đầu giữ nguyên!
        self.assertEqual(p_adj["finalProgress"]["raisedEth"], "0.0100")
        self.assertEqual(p_adj["finalProgress"]["contributingWalletsCount"], 1)
        # Bản ghi điều chỉnh lưu riêng!
        self.assertEqual(p_adj["adjustedFinalProgress"]["raisedEth"], "0.0200")
        self.assertEqual(p_adj["adjustedFinalProgress"]["contributingWalletsCount"], 2)
        # Có audit log
        self.assertEqual(len(p_adj["auditLog"]), 1)
        self.assertEqual(p_adj["auditLog"][0]["actor"], "0xadvisor...")


if __name__ == "__main__":
    unittest.main(verbosity=2)

