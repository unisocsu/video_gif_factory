import os
import sys
import shutil
import tempfile
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "ממיר וידאו ל-GIF"

# (תיאור לציבור, רוחב בפיקסלים)
RESOLUTIONS = [
    ("קטן - 320 פיקסל רוחב (הקובץ הקטן ביותר, מתאים לשליחה בוואטסאפ)", 320),
    ("בינוני - 480 פיקסל רוחב (איכות טובה וגודל סביר)", 480),
    ("גדול - 640 פיקסל רוחב (איכות גבוהה, הקובץ גדול יותר)", 640),
]

# (תיאור לציבור, פריימים בשנייה)
FPS_OPTIONS = [
    ("10 פריימים בשנייה - הכי קטן, התנועה פחות חלקה", 10),
    ("12 פריימים בשנייה - איזון טוב בין גודל לחלקות", 12),
    ("15 פריימים בשנייה - תנועה חלקה, הקובץ גדול יותר", 15),
]


def find_ffmpeg():
    """מחפש את ffmpeg: קודם ליד התוכנה (או בתוך ה-exe), ואחר כך במערכת."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
    name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    local = os.path.join(base, name)
    if os.path.exists(local):
        return local
    return shutil.which("ffmpeg")


def run_ffmpeg(cmd):
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    subprocess.run(cmd, check=True, capture_output=True, creationflags=flags)


def convert(ffmpeg, src, dst, width, fps, seconds):
    """ממיר וידאו ל-GIF בשני שלבים: קודם יוצר פלטה של צבעים, ואז מרכיב את ה-GIF.
    שיטה זו שומרת על איכות טובה ומקטינה משמעותית את הקובץ."""
    tmpdir = tempfile.mkdtemp()
    palette = os.path.join(tmpdir, "palette.png")
    duration = ["-t", str(seconds)] if seconds > 0 else []
    filters = f"fps={fps},scale={width}:-1:flags=lanczos"
    try:
        run_ffmpeg([
            ffmpeg, "-y", "-i", src, *duration,
            "-vf", f"{filters},palettegen=max_colors=128:stats_mode=diff",
            palette,
        ])
        run_ffmpeg([
            ffmpeg, "-y", "-i", src, "-i", palette, *duration,
            "-lavfi", f"{filters}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
            "-loop", "0",
            dst,
        ])
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("640x430")
        self.resizable(False, False)

        self.src = tk.StringVar()
        self.res_var = tk.StringVar(value=RESOLUTIONS[0][0])
        self.fps_var = tk.StringVar(value=FPS_OPTIONS[1][0])
        self.sec_var = tk.StringVar(value="0")
        self.status = tk.StringVar(value="בחרו קובץ וידאו כדי להתחיל")

        self.build()

    def build(self):
        pad = {"padx": 12, "pady": 6}

        tk.Label(self, text="שלב 1: בחירת קובץ וידאו", font=("Arial", 12, "bold")).pack(anchor="e", **pad)
        row = tk.Frame(self)
        row.pack(fill="x", **pad)
        tk.Button(row, text="בחירת קובץ...", command=self.pick_file, width=14).pack(side="right")
        tk.Entry(row, textvariable=self.src, state="readonly", justify="right").pack(side="right", fill="x", expand=True, padx=8)

        tk.Label(self, text="שלב 2: בחירת איכות (רזולוציה)", font=("Arial", 12, "bold")).pack(anchor="e", **pad)
        ttk.Combobox(self, textvariable=self.res_var, values=[r[0] for r in RESOLUTIONS],
                     state="readonly", width=70, justify="right").pack(**pad)

        tk.Label(self, text="שלב 3: מהירות התנועה (פריימים בשנייה)", font=("Arial", 12, "bold")).pack(anchor="e", **pad)
        ttk.Combobox(self, textvariable=self.fps_var, values=[f[0] for f in FPS_OPTIONS],
                     state="readonly", width=70, justify="right").pack(**pad)

        tk.Label(self, text="שלב 4: אורך ה-GIF בשניות (0 = כל הסרטון)", font=("Arial", 12, "bold")).pack(anchor="e", **pad)
        tk.Spinbox(self, from_=0, to=600, textvariable=self.sec_var, width=8, justify="right").pack(anchor="e", **pad)
        tk.Label(self, text="טיפ: קטע קצר יותר = קובץ קטן יותר", fg="gray").pack(anchor="e", padx=12)

        self.btn = tk.Button(self, text="המר ל-GIF", command=self.start,
                             font=("Arial", 12, "bold"), bg="#2e7d32", fg="white", height=2, width=20)
        self.btn.pack(pady=14)

        tk.Label(self, textvariable=self.status, fg="#333").pack(pady=4)

    def pick_file(self):
        path = filedialog.askopenfilename(
            title="בחרו קובץ וידאו",
            filetypes=[("קבצי וידאו", "*.mp4 *.mov *.avi *.mkv *.wmv *.webm *.3gp"), ("כל הקבצים", "*.*")],
        )
        if path:
            self.src.set(path)
            self.status.set("מוכן להמרה")

    def start(self):
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            messagebox.showerror(APP_TITLE, "לא נמצא ffmpeg.\nהניחו את הקובץ ffmpeg.exe באותה תיקייה של התוכנה.")
            return

        src = self.src.get()
        if not src:
            messagebox.showwarning(APP_TITLE, "יש לבחור קובץ וידאו קודם.")
            return

        try:
            seconds = float(self.sec_var.get() or 0)
            if seconds < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(APP_TITLE, "אורך ה-GIF חייב להיות מספר חיובי (או 0 לכל הסרטון).")
            return

        default_name = os.path.splitext(os.path.basename(src))[0] + ".gif"
        dst = filedialog.asksaveasfilename(
            title="שמירת ה-GIF",
            defaultextension=".gif",
            initialfile=default_name,
            filetypes=[("GIF", "*.gif")],
        )
        if not dst:
            return

        width = dict(RESOLUTIONS)[self.res_var.get()]
        fps = dict(FPS_OPTIONS)[self.fps_var.get()]

        self.btn.config(state="disabled")
        self.status.set("ממיר... זה עשוי לקחת כמה דקות בסרטונים ארוכים")
        threading.Thread(
            target=self.worker, args=(ffmpeg, src, dst, width, fps, seconds), daemon=True
        ).start()

    def worker(self, ffmpeg, src, dst, width, fps, seconds):
        try:
            convert(ffmpeg, src, dst, width, fps, seconds)
            size_kb = os.path.getsize(dst) / 1024
            msg = f"ההמרה הושלמה! הקובץ נשמר ({size_kb:,.0f} KB)"
            self.after(0, lambda: self.finish(msg, success=True))
        except subprocess.CalledProcessError:
            self.after(0, lambda: self.finish("ההמרה נכשלה. ודאו שהקובץ הוא וידאו תקין.", success=False))
        except Exception as exc:
            self.after(0, lambda: self.finish(f"שגיאה: {exc}", success=False))

    def finish(self, msg, success):
        self.btn.config(state="normal")
        self.status.set(msg)
        if success:
            messagebox.showinfo(APP_TITLE, msg)
        else:
            messagebox.showerror(APP_TITLE, msg)


if __name__ == "__main__":
    App().mainloop()
