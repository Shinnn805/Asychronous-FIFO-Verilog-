
import argparse
import os
import random
import sys
from collections import deque
from dataclasses import dataclass, field, replace
from typing import List

# ----------------------------------------------------------- tham so (khop RTL / TB)
DATA_WIDTH = 8
PTR_WIDTH = 3                      # DEPTH = 8 (giong testbench)
DEPTH = 1 << PTR_WIDTH
AF_THRESH = 2                      # ALMOST_FULL_THRESH
AE_THRESH = 2                      # ALMOST_EMPTY_THRESH
AF_LEVEL = DEPTH - AF_THRESH

PMASK = (1 << (PTR_WIDTH + 1)) - 1  # con tro P+1 bit
AMASK = DEPTH - 1                   # dia chi RAM
DMASK = (1 << DATA_WIDTH) - 1


def bin2gray(b: int) -> int:
    return (b ^ (b >> 1)) & PMASK


def gray2bin(g: int) -> int:
    """Giong ham gray2bin trong RTL."""
    b = g & (1 << PTR_WIDTH)
    for i in range(PTR_WIDTH - 1, -1, -1):
        bit = ((b >> (i + 1)) & 1) ^ ((g >> i) & 1)
        b |= bit << i
    return b


# ============================================================================
#  Mo hinh cycle-accurate
# ============================================================================
@dataclass
class Inputs:
    wrst: int = 1
    rrst: int = 1
    w_en: int = 0
    r_en: int = 0
    data_in: int = 0


@dataclass
class State:
    # --- mien ghi (wptr_handler + sync_rptr)
    b_wptr: int = 0
    g_wptr: int = 0
    full: int = 0
    almost_full: int = 0
    sr_s1: int = 0                 # synchronizer: g_rptr -> wclk (stage1)
    sr_d: int = 0                  # d_out
    # --- mien doc (rptr_handler + sync_wptr)
    b_rptr: int = 0
    g_rptr: int = 0
    empty: int = 1
    almost_empty: int = 1
    sw_s1: int = 0                 # synchronizer: g_wptr -> rclk (stage1)
    sw_d: int = 0
    # --- RAM + data_out (khong co reset, giong RTL)
    mem: List[int] = field(default_factory=lambda: [0] * DEPTH)
    data_out: int = 0
    data_valid: bool = False       # False = 'x' (chua doc lan nao)


class AsyncFifoModel:
    def __init__(self):
        self.s = State()

    def step(self, wpos: bool, rpos: bool, inp: Inputs) -> None:
        """Mot thoi diem mo phong. wpos/rpos = co canh LEN cua wclk/rclk.
        Hai mien cung doc trang thai TRUOC canh (nhu non-blocking assignment)."""
        o = replace(self.s, mem=list(self.s.mem))     # anh chup truoc canh
        if wpos and not inp.wrst:
            self._write_edge(o, inp)
        if rpos and not inp.rrst:
            self._read_edge(o, inp)
        if inp.wrst:                                   # reset bat dong bo
            self._reset_write_domain()
        if inp.rrst:
            self._reset_read_domain()

    def _reset_write_domain(self):
        s = self.s
        s.b_wptr = s.g_wptr = 0
        s.full = s.almost_full = 0
        s.sr_s1 = s.sr_d = 0

    def _reset_read_domain(self):
        s = self.s
        s.b_rptr = s.g_rptr = 0
        s.empty = s.almost_empty = 1
        s.sw_s1 = s.sw_d = 0

    def _write_edge(self, o: State, inp: Inputs):
        s = self.s
        wen_eff = inp.w_en and not o.full
        b_next = (o.b_wptr + (1 if wen_eff else 0)) & PMASK
        g_next = bin2gray(b_next)
        # full: g_wptr_next == {~g_rptr_sync[P:P-1], g_rptr_sync[P-2:0]}
        cmp_ = (o.sr_d ^ (3 << (PTR_WIDTH - 1))) & PMASK
        wfull = int(g_next == cmp_)
        fill = (b_next - gray2bin(o.sr_d)) & PMASK
        walmost = int(fill >= AF_LEVEL)

        if wen_eff:
            s.mem[o.b_wptr & AMASK] = inp.data_in & DMASK
        s.b_wptr, s.g_wptr = b_next, g_next
        s.full, s.almost_full = wfull, walmost
        s.sr_d = o.sr_s1               # 2FF: d_out <= stage1
        s.sr_s1 = o.g_rptr             #      stage1 <= d_in

    def _read_edge(self, o: State, inp: Inputs):
        s = self.s
        ren_eff = inp.r_en and not o.empty
        b_next = (o.b_rptr + (1 if ren_eff else 0)) & PMASK
        g_next = bin2gray(b_next)
        rempty = int(g_next == o.sw_d)
        fill = (gray2bin(o.sw_d) - b_next) & PMASK
        ralmost = int(fill <= AE_THRESH)

        if ren_eff:                    # doc dong bo: dung RAM TRUOC canh
            s.data_out = o.mem[o.b_rptr & AMASK]
            s.data_valid = True
        s.b_rptr, s.g_rptr = b_next, g_next
        s.empty, s.almost_empty = rempty, ralmost
        s.sw_d = o.sw_s1
        s.sw_s1 = o.g_wptr


# ============================================================================
#  Sinh kich thich + kiem tra cheo
# ============================================================================
NS = 1000  # ps


@dataclass
class Phase:
    name: str
    dur_ps: int          
    w_half_ps: int      
    r_half_ps: int       
    p_w: int             
    p_r: int             


PHASES = [
    Phase("idle sau reset",              1000 * NS, 10 * NS, 35 * NS,   0,   0),
    Phase("chi ghi (ghi khi full)",       800 * NS, 10 * NS, 35 * NS, 100,   0),
    Phase("nghi",                         800 * NS, 10 * NS, 35 * NS,   0,   0),
    Phase("chi doc (doc khi empty)",     2000 * NS, 10 * NS, 35 * NS,   0, 100),
    Phase("nghi",                         600 * NS, 10 * NS, 35 * NS,   0,   0),
    Phase("ngau nhien: wclk nhanh",     60000 * NS, 10 * NS, 35 * NS,  85,  35),
    Phase("ngau nhien: rclk nhanh",     60000 * NS, 35 * NS, 10 * NS,  35,  85),
    Phase("ngau nhien: clock gan bang", 40000 * NS, 10 * NS, 11 * NS,  60,  60),  # reset giua phien o day
    Phase("ghi/doc moi chu ky",         40000 * NS, 17 * NS, 10 * NS, 100, 100),
    Phase("cung tan so",                30000 * NS, 10 * NS, 10 * NS,  50,  50),
    Phase("xa het du lieu",             20000 * NS, 10 * NS, 35 * NS,   0, 100),
    Phase("nghi cuoi",                   2000 * NS, 10 * NS, 35 * NS,   0,   0),
]


def hex_out(s: State) -> str:
    digits = (DATA_WIDTH + 3) // 4
    if not s.data_valid:
        return "x" * digits
    return format(s.data_out & DMASK, "0%dx" % digits)


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden model Python cho asynchronous_fifo")
    ap.add_argument("--seed", type=lambda x: int(x, 0), default=0x5EED1234)
    ap.add_argument("--dir", default=".")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rnd = rng.randrange
    os.makedirs(args.dir, exist_ok=True)
    fs = open(os.path.join(args.dir, "stim.txt"), "w")
    fe = open(os.path.join(args.dir, "expected.txt"), "w")

    # cua so reset (ps): dau phien + giua phien (dau phase "clock gan bang")
    mid_reset = sum(p.dur_ps for p in PHASES[:7])
    rst_win = [(0, 200 * NS), (mid_reset, mid_reset + 200 * NS)]

    def want_reset(t):
        return any(a <= t < b for a, b in rst_win)

    m = AsyncFifoModel()
    inp = Inputs()                      # wrst = rrst = 1
    ideal = deque()                     # FIFO ly tuong
    errors = ovf = udf = tot_w = tot_r = lines = max_occ = 0

    def emit(t, wclk, rclk):
        nonlocal lines
        fs.write("%d %d %d %d %d %d %d %02x\n" %
                 (t, wclk, rclk, inp.wrst, inp.rrst, inp.w_en, inp.r_en,
                  inp.data_in & DMASK))
        s = m.s
        fe.write("%d %d %d %d %d %s\n" %
                 (t, s.full, s.almost_full, s.empty, s.almost_empty, hex_out(s)))
        lines += 1

    # ---- thoi diem 0: reset dang bat
    m.step(False, False, inp)
    emit(0, 0, 0)

    wclk = rclk = 0
    pi = 0
    phase_end = PHASES[0].dur_ps
    wh, rh = PHASES[0].w_half_ps, PHASES[0].r_half_ps
    pw, pr = PHASES[0].p_w, PHASES[0].p_r
    nw, nr = wh, rh                     # lan dao chieu ke tiep
    print("Golden model: seed=0x%x, DEPTH=%d, AF_LEVEL=%d, AE_THRESH=%d" %
          (args.seed, DEPTH, AF_LEVEL, AE_THRESH))
    print("  phase 1/%d: %s" % (len(PHASES), PHASES[0].name))

    done = False
    while not done:
        t = min(nw, nr)
        while t >= phase_end:           # chuyen phase
            pi += 1
            if pi == len(PHASES):
                done = True
                break
            ph = PHASES[pi]
            phase_end += ph.dur_ps
            wh, rh, pw, pr = ph.w_half_ps, ph.r_half_ps, ph.p_w, ph.p_r
            print("  phase %d/%d: %s" % (pi + 1, len(PHASES), ph.name))
        if done:
            break

        wt, rt = (t == nw), (t == nr)
        wpos = rpos = wneg = rneg = False
        if wt:
            wclk ^= 1
            nw = t + wh
            wpos, wneg = bool(wclk), not wclk
        if rt:
            rclk ^= 1
            nr = t + rh
            rpos, rneg = bool(rclk), not rclk

        # ---- kich thich thay doi o CANH XUONG (giong testbench)
        if wneg:
            inp.w_en = int(rnd(100) < pw)
            inp.data_in = rnd(256)
            wr = int(want_reset(t))
            if wr != inp.wrst and not rt:   # doi reset dong thoi 2 mien, tranh trung canh len rclk
                inp.wrst = inp.rrst = wr
        if rneg:
            inp.r_en = int(rnd(100) < pr)

        # ---- kiem tra cheo voi FIFO ly tuong (tinh tu trang thai TRUOC canh)
        pre = m.s
        in_reset = inp.wrst or inp.rrst
        acc_w = wpos and not inp.wrst and inp.w_en and not pre.full
        acc_r = rpos and not inp.rrst and inp.r_en and not pre.empty
        if in_reset:
            ideal.clear()
        else:
            if wpos and inp.w_en and pre.full:
                ovf += 1
            if rpos and inp.r_en and pre.empty:
                udf += 1
            if wpos and not pre.full and len(ideal) == DEPTH:
                print("[%d ps] LOI: FIFO thuc su day nhung full=0" % t)
                errors += 1
            if rpos and not pre.empty and not ideal:
                print("[%d ps] LOI: empty=0 nhung FIFO thuc su rong" % t)
                errors += 1
        expect = None
        if acc_r:                       # doc truoc ghi neu trung canh
            if not ideal:
                print("[%d ps] LOI: UNDERFLOW" % t)
                errors += 1
            else:
                expect = ideal.popleft()
                tot_r += 1
        if acc_w:
            ideal.append(inp.data_in & DMASK)
            tot_w += 1
            if len(ideal) > DEPTH:
                print("[%d ps] LOI: OVERFLOW (%d > %d)" % (t, len(ideal), DEPTH))
                errors += 1
            max_occ = max(max_occ, len(ideal))

        m.step(wpos, rpos, inp)

        if expect is not None and m.s.data_out != expect:
            print("[%d ps] LOI DU LIEU: mong doi %02x, model cho %02x" %
                  (t, expect, m.s.data_out))
            errors += 1
        emit(t, wclk, rclk)

    fs.close()
    fe.close()

    print("\n================ TONG KET GOLDEN MODEL ================")
    print("  So dong stim/expected      : %d" % lines)
    print("  Giao dich ghi / doc        : %d / %d" % (tot_w, tot_r))
    print("  Con tro quay vong          : ~%d lan" % (tot_w // (2 * DEPTH)))
    print("  Ghi khi full bi chan       : %d lan" % ovf)
    print("  Doc khi empty bi chan      : %d lan" % udf)
    print("  Muc day toi da             : %d / %d" % (max_occ, DEPTH))
    print("  Loi so voi FIFO ly tuong   : %d" % errors)
    print("  Ket qua                    : %s" % ("MODEL OK" if errors == 0 else "MODEL FAIL"))
    print("  Da ghi: %s/stim.txt, %s/expected.txt" % (args.dir, args.dir))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
