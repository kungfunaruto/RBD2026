# วิธีทำเป็นไฟล์ .exe เดียว (ฝัง database ไว้ข้างในเลย)

> **สำคัญที่สุดก่อนอื่นใด:** ต้องรันคำสั่ง build นี้ **บนเครื่อง Windows เท่านั้น**
> (จะเป็นเครื่องจริง หรือ Windows VM ก็ได้) เพราะ PyInstaller ไม่สามารถ
> "ข้ามระบบปฏิบัติการ" ได้ — ถ้า build บน Mac จะได้โปรแกรมสำหรับ Mac
> ไม่ใช่ .exe สำหรับ Windows (อธิบายเพิ่มด้านล่างสุด)

## ขั้นตอน (ทำบนเครื่อง Windows)

1. เตรียมโฟลเดอร์โปรเจกต์ให้มีหน้าตาแบบนี้:
   ```
   ThaiWordChecker\
     word_judge.py
     database\
       words.txt      <-- ใส่คำศัพท์ของคุณตรงนี้ (1 คำต่อ 1 บรรทัด, บันทึกเป็น UTF-8)
   ```

2. ติดตั้ง Python 3 จาก https://www.python.org/downloads/windows/
   ตอนติดตั้งให้ติ๊ก "Add python.exe to PATH" ด้วย

3. เปิด Command Prompt (cmd) แล้วไปที่โฟลเดอร์โปรเจกต์ เช่น
   ```
   cd C:\Users\yourname\Desktop\ThaiWordChecker
   ```

4. ติดตั้ง PyInstaller:
   ```
   pip install pyinstaller
   ```

5. สั่ง build เป็นไฟล์เดียว พร้อมฝัง database\words.txt เข้าไปในตัว exe:
   ```
   window
   pyinstaller --onefile --noconsole --name "ThaiWordChallenge" --add-data "database\words.txt;database" RBD2026.py

   mac
   pyinstaller --onefile --windowed --name "ThaiWordChallenge" --add-data "database/words.txt:database" RBD2026.py
   ```
   - `--onefile` = รวมทุกอย่างเป็น .exe ไฟล์เดียว
   - `--noconsole` = ไม่ให้เด้งหน้าต่างจอดำ (console) ขึ้นมาด้วย
   - `--add-data "database\words.txt;database"` = ฝังไฟล์ words.txt เข้าไปในตัวโปรแกรม
     (บน Windows ตัวคั่น src กับ dest ต้องเป็น `;` — ถ้า build บน mac/linux ต้องใช้ `:` แทน)

6. เสร็จแล้วไฟล์จะอยู่ที่ `dist\ThaiWordChecker.exe`
   ไฟล์นี้ไฟล์เดียวส่งต่อให้ใครก็ได้เลย ไม่ต้องติดตั้ง Python เพิ่ม
   ดับเบิลคลิกแล้วรันได้ทันที

## ข้อควรรู้เมื่อฝัง database ไว้ข้างใน .exe

- database จะกลายเป็นส่วนหนึ่งของตัวโปรแกรม **แก้ไขไม่ได้อีกแล้ว** (แม้จะกด F5
  ในโปรแกรมก็แค่โหลดชุดเดิมที่ฝังไว้ซ้ำ) ถ้าต้องการอัปเดตคำศัพท์ในอนาคต
  ต้องแก้ไฟล์ `database\words.txt` แล้ว build ใหม่ทุกครั้ง
- ถ้าอยากให้แก้ไข database ได้โดยไม่ต้อง build ใหม่ ให้ตัด `--add-data`
  ออก แล้ววางโฟลเดอร์ `database\` ไว้ข้าง ๆ ไฟล์ .exe แทน (ต้องแจกไป 2
  อย่างคือ .exe + โฟลเดอร์ database แทนที่จะเป็นไฟล์เดียว)

## ถ้าไม่มีเครื่อง Windows จริง ๆ

ทางเลือกที่ทำได้โดยไม่ต้องซื้อ/ยืมเครื่อง Windows:

- **GitHub Actions (แนะนำ):** อัปโค้ดขึ้น GitHub repo แล้วตั้ง workflow ให้รันบน
  `windows-latest` runner ซึ่งจะ build .exe ให้อัตโนมัติทุกครั้งที่ push แล้วให้
  ดาวน์โหลดไฟล์ที่ build เสร็จกลับมา (ฟรีสำหรับ public repo) ตัวอย่าง workflow
  คร่าว ๆ:
  ```yaml
  # .github/workflows/build.yml
  on: [push]
  jobs:
    build:
      runs-on: windows-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with: { python-version: '3.11' }
        - run: pip install pyinstaller
        - run: pyinstaller --onefile --noconsole --name "ThaiWordChecker" --add-data "database\words.txt;database" word_judge.py
        - uses: actions/upload-artifact@v4
          with: { name: ThaiWordChecker-exe, path: dist/ThaiWordChecker.exe }
  ```
- **Windows VM บน Mac:** Parallels / VMware Fusion / VirtualBox ลง Windows แล้ว
  build ตามขั้นตอนด้านบนตามปกติ
- **ไม่แนะนำ:** การใช้ Wine บน Mac เพื่อรัน PyInstaller ข้ามระบบ มักมีปัญหากับ
  Tkinter/Tcl-Tk โดยเฉพาะ ผลลัพธ์ไม่เสถียรและดีบักยาก
