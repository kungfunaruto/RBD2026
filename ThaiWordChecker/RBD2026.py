"""
Thai Word Checker
=================
โปรแกรมตรวจสอบคำศัพท์ภาษาไทย ควบคุมด้วยคีย์บอร์ดทั้งหมด (ไม่ต้องใช้เมาส์)
สไตล์หน้าจอเลียนแบบ Collins Zyzzyva Word Judge

วิธีใช้งาน:
  1. เปิดโปรแกรม -> พิมพ์ "จำนวนคำ" ที่ต้องการตรวจสอบ -> กด Enter
  2. โปรแกรมไปหน้าพิมพ์คำอัตโนมัติ -> พิมพ์คำ -> กด Enter เพื่อขึ้นบรรทัดใหม่ (คำถัดไป)
  3. เมื่อพิมพ์ครบจำนวน -> กด Tab เพื่อ "ตรวจสอบ"
  4. ผลลัพธ์: ✓ = มีความหมายครบทุกคำ, ✕ = ไม่พบอย่างน้อย 1 คำ (ไม่ระบุว่าคำไหน)
  5. กด "ปุ่มใดก็ได้" ที่หน้าผลลัพธ์เพื่อล้างและเริ่มรอบใหม่ หรือรอ 7 วินาทีให้กลับเองอัตโนมัติ
  6. ที่หน้าพิมพ์คำ กด Esc เพื่อย้อนกลับไปหน้าเลือกจำนวนคำ

ฐานข้อมูล:
  ไฟล์ database/words.txt — 1 คำต่อ 1 บรรทัด
  (เมื่อ build เป็น .exe แบบ onefile ไฟล์นี้จะถูกฝังไว้ข้างในโปรแกรมเลย
   ดูวิธี build ได้ในไฟล์ BUILD_EXE.md ที่แนบมาด้วย)
"""

import tkinter as tk
from tkinter import font
import os
import sys
import datetime

if getattr(sys, "frozen", False):
    # เมื่อถูก build เป็น .exe ด้วย PyInstaller (โหมด --onefile) ไฟล์ข้อมูลที่
    # แนบไปด้วย --add-data จะถูกแตกไปไว้ในโฟลเดอร์ชั่วคราวที่ sys._MEIPASS ชี้ถึง
    # ไม่ใช่โฟลเดอร์เดียวกับตัว .exe จึงต้องเช็คตรงนี้ก่อน ไม่งั้นหาไฟล์ไม่เจอ
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_DIR = os.path.join(BASE_DIR, "database")
DB_FILE = os.path.join(DB_DIR, "words.txt")

# ---------------------------------------------------------------------------
# Palette (slightly refreshed, still light/neutral so it stays easy to read)
# ---------------------------------------------------------------------------

COLOR_BG = "#f5f6f8"
COLOR_PANEL_BG = "#ffffff"
COLOR_TOPBAR = "#111111"
COLOR_TEXT = "#1a1a1a"
COLOR_MUTED = "#555555"
COLOR_FAINT = "#8a8a8a"
COLOR_PANEL_BORDER = "#e2e2e2"
COLOR_ACCENT = "#2b6cb0"
COLOR_GOOD = "#2e7d32"
COLOR_GOOD_BG = "#eaf6ec"
COLOR_BAD = "#c62828"
COLOR_BAD_BG = "#fdecea"
COLOR_BADGE_BG = "#e0632b"
COLOR_BADGE_FG = "#ffffff"

RESULT_AUTO_CLOSE_MS = 7000  # หน้าผลลัพธ์จะเด้งกลับหน้าแรกเองหลังจากนี้ ถ้าไม่กดอะไรเลย

# Thai digit / lookalike-character normalization so users don't have to
# keep switching keyboard language back and forth just to type numbers.
#   - Full set of Thai numerals (๐-๙) map to 0-9.
#   - "ๅ" (LAKKHANGYAO) also maps to "1" on request, since it sits in a
#     spot people keep hitting by habit when they forget to switch layout.
THAI_DIGIT_MAP = {
    "จ": "0", "ๅ": "1", "/": "2", "_": "3", "ภ": "4",
    "ถ": "5", "ุ": "6", "ึ": "7", "ค": "8", "ต": "9",

}


def load_words():
    """โหลดรายการคำศัพท์จากไฟล์ database/words.txt"""
    words = set()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w and not w.startswith("#"):
                    words.add(w)
    return words


class ThaiWordChecker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Thai Word Challenge")
        self.geometry("1000x680")
        self.minsize(760, 560)
        self.configure(bg=COLOR_BG)

        # ---- fullscreen support ---------------------------------------
        # Real, resizable window by default, plus a one-key toggle for a
        # true borderless fullscreen mode. F11 toggles it, Escape leaves it
        # (Escape also has extra meaning on the word-entry screen, see
        # on_word_escape below).
        self.resizable(True, True)
        self.is_fullscreen = False
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)
        try:
            # Start maximized (keeps window chrome) on platforms that support it.
            self.state("zoomed")
        except tk.TclError:
            self.eval("tk::PlaceWindow . center")

        self.words_db = load_words()
        self.target_count = 0
        self.entered_words = []
        self.last_missing_words = []
        self.stage = "count"  # count -> word -> result
        self._count_advance_job = None
        self._result_auto_close_job = None

        # Pick the best available Thai-friendly font on this machine.
        available_families = set(font.families())
        for candidate in ("Leelawadee UI", "TH Sarabun New", "Tahoma", "Segoe UI"):
            if candidate in available_families:
                base_family = candidate
                break
        else:
            base_family = "Tahoma"

        self.font_h1 = font.Font(family=base_family, size=16, weight="bold")
        self.font_body = font.Font(family=base_family, size=20)
        self.font_small = font.Font(family=base_family, size=15)
        self.font_count = font.Font(family=base_family, size=120, weight="bold")
        self.font_word = font.Font(family=base_family, size=40)
        self.font_result_icon = font.Font(family=base_family, size=90, weight="bold")
        self.font_result_headline = font.Font(family=base_family, size=22, weight="bold")
        self.font_result_words = font.Font(family=base_family, size=40)

        self._build_chrome()
        self._build_count_screen()
        self._build_word_screen()
        self._build_result_screen()
        self._bind_global_keys()
        self.show_count_stage()

    # ---------------- fullscreen helpers ----------------
    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        return "break"

    def exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
        return "break"

    # ---------------- static chrome (top bar + footer) ----------------
    def _build_chrome(self):
        self.topbar = tk.Frame(self, bg=COLOR_TOPBAR, height=6)
        self.topbar.pack(side="top", fill="x")

        footer = tk.Frame(self, bg=COLOR_BG)
        footer.pack(side="bottom", fill="x", padx=18, pady=10)

        left = tk.Label(footer, text="Thai Word Challenge\nVersion 1.2",
                         font=self.font_small, bg=COLOR_BG, fg=COLOR_FAINT,
                         justify="left")
        left.pack(side="left")

        badge = tk.Label(footer, text="ท", font=font.Font(family=self.font_small.actual("family"), size=14, weight="bold"),
                          bg=COLOR_BADGE_BG, fg=COLOR_BADGE_FG, width=2, height=1)
        badge.pack(side="left", padx=20)

        today = datetime.date.today().strftime("%d %b %Y")
        self.db_label = tk.Label(footer, text="", font=self.font_small,
                                  bg=COLOR_BG, fg=COLOR_FAINT, justify="right")
        self.db_label.pack(side="right")
        self._today_text = today
        self._refresh_db_label()

    def _refresh_db_label(self):
        self.db_label.config(
            ##text=f"ฐานข้อมูล: {len(self.words_db)} คำ   (F11 = เต็มจอ)\n{self._today_text}"
        )

    # ---------------- screen: count ----------------
    def _build_count_screen(self):
        self.count_frame = tk.Frame(self, bg=COLOR_BG)

        tk.Label(self.count_frame, text="CHALLENGER:", font=self.font_h1,
                 bg=COLOR_BG, fg=COLOR_TEXT).pack(pady=(60, 4))
        tk.Label(self.count_frame, text="ต้องการตรวจสอบกี่คำ?", font=self.font_body,
                 bg=COLOR_BG, fg=COLOR_MUTED).pack()

        self.count_var = tk.StringVar()
        self.count_display = tk.Label(self.count_frame, textvariable=self.count_var,
                                       font=self.font_count, bg=COLOR_BG, fg=COLOR_TEXT)
        self.count_display.pack(pady=120)


    # ---------------- screen: word entry ----------------
    def _build_word_screen(self):
        self.word_frame = tk.Frame(self, bg=COLOR_BG)

        self.instructions = tk.Label(
            self.word_frame, font=self.font_body, bg=COLOR_BG, fg=COLOR_TEXT,
            justify="center", anchor="center"
        )
        self.instructions.pack(pady=(24, 14), fill="x")

        panel = tk.Frame(self.word_frame, bg=COLOR_PANEL_BG, highlightbackground=COLOR_PANEL_BORDER,
                          highlightthickness=1)
        panel.pack(padx=40, pady=6, fill="both", expand=True)

        self.word_text = tk.Text(panel, font=self.font_word, bg=COLOR_PANEL_BG, fg=COLOR_TEXT,
                                  relief="flat", padx=24, pady=20, wrap="none",
                                  insertbackground=COLOR_TEXT, height=10, spacing3=6)
        self.word_text.pack(fill="both", expand=True)

        # Order matters: bind the specific keys first (Return / Tab /
        # BackSpace / Delete / Escape) so they take priority over the
        # generic <Key> catch-all added right after with add="+".
        self.word_text.bind("<Return>", self.on_word_return)
        self.word_text.bind("<Tab>", self.on_tab)
        self.word_text.bind("<BackSpace>", self.on_word_backspace)
        self.word_text.bind("<Delete>", self.on_word_delete)
        self.word_text.bind("<Escape>", self.on_word_escape)
        self.word_text.bind("<Key>", self.on_any_key_in_word_stage, add="+")

    # ---------------- screen: result ----------------
    def _build_result_screen(self):
        self.result_frame = tk.Frame(self, bg=COLOR_BG)

        # Colored accent bar across the top of the card, mirroring the
        # reference design (green = acceptable, red = not acceptable).
        self.result_accent = tk.Frame(self.result_frame, height=8, bg=COLOR_GOOD)
        self.result_accent.pack(side="top", fill="x")

        card = tk.Frame(self.result_frame, bg=COLOR_PANEL_BG,
                         highlightbackground=COLOR_PANEL_BORDER, highlightthickness=1)
        card.pack(padx=60, pady=40, fill="both", expand=True)

        center = tk.Frame(card, bg=COLOR_PANEL_BG)
        center.place(relx=0.5, rely=0.5, anchor="center")

        self.result_icon_label = tk.Label(center, text="", font=self.font_result_icon,
                                           bg=COLOR_PANEL_BG, fg=COLOR_GOOD)
        self.result_icon_label.pack(pady=(0, 10))

        self.result_headline_label = tk.Label(center, text="", font=self.font_result_headline,
                                               bg=COLOR_PANEL_BG, fg=COLOR_GOOD)
        self.result_headline_label.pack()

        self.result_words_label = tk.Label(center, text="", font=self.font_result_words,
                                            bg=COLOR_PANEL_BG, fg=COLOR_TEXT, wraplength=760,
                                            justify="center")
        self.result_words_label.pack(pady=(18, 0))

        self.result_detail_label = tk.Label(center, text="", font=self.font_small,
                                             bg=COLOR_PANEL_BG, fg=COLOR_BAD, wraplength=760,
                                             justify="center")
        self.result_detail_label.pack(pady=(8, 0))

        self.result_hint_label = tk.Label(
            card, text="กด ปุ่มใดก็ได้ เพื่อล้างผลลัพธ์",
            font=self.font_small, bg=COLOR_PANEL_BG, fg=COLOR_FAINT)
        self.result_hint_label.place(relx=0.5, rely=0.93, anchor="center")

    def _set_instructions(self, lines):
        self.instructions.config(text="\n".join(lines))

    # ---------------- global keys ----------------
    def _bind_global_keys(self):
        self.bind("<F5>", self.on_reload_db)

    # ---------------- stage transitions ----------------
    def show_count_stage(self):
        self._cancel_count_auto_advance()
        self._cancel_result_auto_close()
        self.stage = "count"
        self.entered_words = []
        self.count_var.set("")
        self.result_frame.pack_forget()
        self.word_frame.pack_forget()
        self.count_frame.pack(fill="both", expand=True)
        self.focus_set()
        self.unbind("<Key>")
        self.bind("<Key>", self.on_count_key)

    def show_word_stage(self):
        self._cancel_count_auto_advance()
        self._cancel_result_auto_close()
        self.stage = "word"
        self.entered_words = []
        self.count_frame.pack_forget()
        self.result_frame.pack_forget()
        self.word_frame.pack(fill="both", expand=True)
        self.unbind("<Key>")

        self._set_instructions([
            f"1. พิมพ์คำ {self.target_count} คำ คั่นด้วย ENTER",
            "2. กด TAB เพื่อตรวจสอบ",
            "3. กด Esc เพื่อย้อนกลับไปเลือกจำนวนคำใหม่",
        ])

        self.word_text.config(state="normal")
        self.word_text.delete("1.0", "end")
        self.word_text.focus_set()

    def show_result(self, ok, words, missing_words):
        self._cancel_result_auto_close()
        self.stage = "result"
        self.word_text.config(state="disabled")
        self.word_frame.pack_forget()
        self.result_frame.pack(fill="both", expand=True)

        words_line = ", ".join(words)

        if ok:
            self.result_accent.config(bg=COLOR_GOOD)
            self.result_icon_label.config(text="\u2713", fg=COLOR_GOOD)  # check mark
            self.result_headline_label.config(
                text="ผ่าน! มีความหมายครบทุกคำ", fg=COLOR_GOOD)
            self.result_words_label.config(text=words_line)
            self.result_detail_label.config(text="")
        else:
            self.result_accent.config(bg=COLOR_BAD)
            self.result_icon_label.config(text="\u2715", fg=COLOR_BAD)  # cross mark
            self.result_headline_label.config(
                text="ไม่ผ่าน พบคำที่ไม่ถูกต้อง", fg=COLOR_BAD)
            self.result_words_label.config(text=words_line)
            self.result_detail_label.config(
                text="มีคำที่ไม่ถูกต้องอย่างน้อย 1 คำ")

        # Any key at all should clear the result. We rely on the
        # word_text-level handlers (which check self.stage == "result")
        # for as long as focus stays there, plus this root-level binding
        # as a safety net if focus ever moves elsewhere.
        self.unbind("<Key>")
        self.bind("<Key>", self.on_result_key)
        self.focus_set()

        # ...and if nobody presses anything at all, auto-return to the
        # count screen after RESULT_AUTO_CLOSE_MS milliseconds.
        self._result_auto_close_job = self.after(
            RESULT_AUTO_CLOSE_MS, self._auto_close_result)

    def clear_result_and_reset(self):
        self.show_count_stage()

    def _cancel_result_auto_close(self):
        if self._result_auto_close_job is not None:
            try:
                self.after_cancel(self._result_auto_close_job)
            except tk.TclError:
                pass
            self._result_auto_close_job = None

    def _auto_close_result(self):
        self._result_auto_close_job = None
        if self.stage == "result":
            self.clear_result_and_reset()

    # ---------------- events: count stage ----------------
    def on_count_key(self, event):
        char = THAI_DIGIT_MAP.get(event.char, event.char)

        if event.keysym == "Return":
            self._cancel_count_auto_advance()
            self._try_start_word_stage()
            return "break"
        if event.keysym == "BackSpace":
            self.count_var.set(self.count_var.get()[:-1])
            self._reschedule_count_auto_advance()
            return "break"
        if char.isdigit():
            self.count_var.set(self.count_var.get() + char)
            self._reschedule_count_auto_advance()
            return "break"
        return "break"

    def _try_start_word_stage(self):
        text = self.count_var.get().strip()
        if text.isdigit() and int(text) > 0:
            self.target_count = int(text)
            self.show_word_stage()
            return True
        return False

    def _reschedule_count_auto_advance(self):
        # Auto-advance to the word screen ~1 second after the last keypress,
        # without requiring an extra Enter. Any further keypress
        # (including backspace) resets the timer.
        self._cancel_count_auto_advance()
        text = self.count_var.get().strip()
        if text.isdigit() and int(text) > 0:
            self._count_advance_job = self.after(1000, self._auto_advance_from_count)

    def _auto_advance_from_count(self):
        self._count_advance_job = None
        if self.stage == "count":
            self._try_start_word_stage()

    def _cancel_count_auto_advance(self):
        if self._count_advance_job is not None:
            try:
                self.after_cancel(self._count_advance_job)
            except tk.TclError:
                pass
            self._count_advance_job = None

    # ---------------- events: word stage ----------------
    def on_word_return(self, event):
        if self.stage == "result":
            self.clear_result_and_reset()
            return "break"

        content = self.word_text.get("1.0", "end-1c")
        lines = content.split("\n")
        current_words = [ln.strip() for ln in lines if ln.strip()]

        if len(current_words) >= self.target_count:
            return "break"  # ครบจำนวนแล้ว ห้ามขึ้นบรรทัดใหม่อีก

        last_line = lines[-1].strip() if lines else ""
        if not last_line:
            return "break"  # ห้ามขึ้นบรรทัดว่าง

        return None  # อนุญาตให้ Enter ทำงานปกติ (ขึ้นบรรทัดใหม่)

    def on_word_backspace(self, event):
        if self.stage == "result":
            self.clear_result_and_reset()
            return "break"
        # Tk's default BackSpace binding on recent versions deletes an
        # entire "grapheme cluster" at once. Thai combining tone marks /
        # vowels (e.g. the mai-tho in "ได้") get bundled with the
        # preceding consonant, so one backspace after typing "ได้" wipes
        # out "ด้" together and leaves only "ไ" instead of the expected
        # "ได". Deleting by an explicit index (exactly one Unicode
        # codepoint) instead of relying on the built-in grapheme aware
        # deletion fixes this.
        self.word_text.delete("insert-1c", "insert")
        return "break"

    def on_word_delete(self, event):
        if self.stage == "result":
            self.clear_result_and_reset()
            return "break"
        self.word_text.delete("insert", "insert+1c")
        return "break"

    def on_word_escape(self, event):
        # ไม่ว่าจะอยู่ระหว่างพิมพ์คำ หรือหน้าผลลัพธ์ (เผื่อโฟกัสยังอยู่ที่กล่องข้อความ)
        # Esc จะพากลับไปหน้าเลือกจำนวนคำเสมอ
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
        self.show_count_stage()
        return "break"

    def on_any_key_in_word_stage(self, event):
        if self.stage == "result":
            self.clear_result_and_reset()
            return "break"

        # ป้องกันไม่ให้พิมพ์เกินจำนวนคำที่กำหนด (ยกเว้นปุ่มควบคุมการเลื่อนเคอร์เซอร์)
        if event.keysym in ("Tab", "Return", "BackSpace", "Delete", "Escape", "Left",
                             "Right", "Up", "Down", "Home", "End"):
            return None
        content = self.word_text.get("1.0", "end-1c")
        lines = content.split("\n")
        current_words = [ln.strip() for ln in lines if ln.strip()]
        on_new_word = (lines[-1].strip() == "")
        if len(current_words) >= self.target_count and on_new_word:
            return "break"
        if len(current_words) > self.target_count:
            return "break"
        return None

    def on_tab(self, event):
        if self.stage == "result":
            self.clear_result_and_reset()
            return "break"

        content = self.word_text.get("1.0", "end-1c")
        words = [ln.strip() for ln in content.split("\n") if ln.strip()]
        if words and len(words) >= self.target_count:
            missing = [w for w in words if w not in self.words_db]
            self.show_result(len(missing) == 0, words, missing)
        return "break"

    # ---------------- events: result stage ----------------
    def on_result_key(self, event):
        self.unbind("<Key>")
        self.clear_result_and_reset()
        return "break"

    # ---------------- misc ----------------
    def on_reload_db(self, event=None):
        self.words_db = load_words()
        self._refresh_db_label()


if __name__ == "__main__":
    os.makedirs(DB_DIR, exist_ok=True)
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            f.write("database error")

    app = ThaiWordChecker()
    app.mainloop()
