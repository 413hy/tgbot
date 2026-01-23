import hashlib


def score_for(block_hash: str, raffle_code: str, participant_no: int) -> tuple[str, int]:
    """Compute a deterministic score for a participant.

    为了避免“同一个区块导致不同抽奖得到完全相同排序”的观感问题，我们把【抽奖编号】也纳入种子：
    score_seed = 区块哈希 + 抽奖编号 + 参与编号

    score = hexdec(SHA256(score_seed) 前16位)
    """
    seed = f"{block_hash}{raffle_code}{participant_no}"
    h = hashlib.sha256(seed.encode()).hexdigest()
    # NOTE:
    # - MySQL column is BIGINT; many drivers bind integers via a signed C long.
    # - int(h[:16], 16) can be up to 2^64-1, which may overflow signed 64-bit.
    # To avoid "Python int too large to convert to C long", clamp to 63 bits.
    score = int(h[:16], 16) & ((1 << 63) - 1)
    return h, score
